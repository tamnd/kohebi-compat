"""A corpus of broken files, made by breaking real ones.

`corpus/broken` is written by hand, which is what makes it good at the cases
someone thought of and useless at the ones nobody did. Every file in it is
short, deliberate, and wrong in exactly one way that a person had in mind. Real
broken Python does not look like that. It is a two hundred line module with a
missing comma four hundred columns in, and the interesting question about it is
usually not what the message says but which of several things that are wrong
with the file gets reported at all.

So this builds the other kind of corpus. Take a module out of the standard
library, which is real code somebody wrote for a reason, break one line of it,
and keep the result if CPython refuses it. Do that a thousand times with a
fixed seed and you have a corpus that nobody designed, which is the point. When
we first pointed it at kohebi it agreed with CPython on 55% of the blocks, and
the largest single bucket was not a message we had got wrong. It was the rule
deciding which of two errors to print, which no hand written case had caught
because a hand written case is only ever wrong in one place.

The five edits are deliberately dull. Delete a token, duplicate a token, swap
two neighbouring tokens, delete a character, insert an operator. Nothing here
is trying to be clever, because the corpus is not a test of how strange an
input can be. It is a sample of what breaking real code looks like, and the
distribution of what CPython says about it is the thing worth having.

Mutants are generated rather than committed. They are derived from a standard
library that differs between machines and Python versions, they are large, and
none of them is worth reading on its own. What is committed is the seed and the
rules, which is enough for two people to get the same corpus.
"""

from __future__ import annotations

import io
import random
import tokenize
from dataclasses import dataclass
from pathlib import Path

OPERATORS = ("=", "+", ",", ":", ")", "(", "]", "*")
"""What `insert` reaches for.

Weighted towards nothing in particular. These are the characters that turn up
in a real typo, and the brackets are here because an unbalanced one is the most
interesting thing that can happen to a file: it breaks a line the tokenizer is
nowhere near, which is exactly the case a hand written corpus never has.
"""


@dataclass(frozen=True)
class Mutant:
    """One broken file and the edit that broke it."""

    name: str
    source: str
    origin: str
    edit: str
    line: int


def sources(root: Path, *, smallest: int, largest: int) -> list[Path]:
    """Modules worth breaking, in a stable order.

    Bounded at both ends. A file of five lines has almost nowhere to put an
    error and the mutant reads like a hand written case, which is the thing
    this corpus exists not to be. A file of four thousand lines takes CPython
    and kohebi long enough to compare that the corpus stops being something
    anyone runs.
    """
    found = []
    for path in sorted(root.rglob("*.py")):
        try:
            lines = path.read_text(encoding="utf-8").count("\n")
        except (OSError, UnicodeDecodeError):
            continue
        if smallest <= lines <= largest:
            found.append(path)
    return found


def line_tokens(line: str) -> list[str] | None:
    """The line split into tokens, or `None` if it does not tokenize alone.

    A single line out of the middle of a file is not a program, so most of what
    `tokenize` raises here is expected and means only that this line is not one
    to break. A continuation line, a line inside a triple quoted string, and a
    line that opens a bracket it does not close all land here.
    """
    try:
        pieces = [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(line).readline)
            if token.string.strip()
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    return pieces or None


def break_line(line: str, rng: random.Random) -> tuple[str, str] | None:
    """One edit applied to one line, with the name of the edit.

    `None` when this line has nothing to break, which is a blank line, a
    comment, or a line the tokenizer will not read on its own.
    """
    body = line.strip()
    if not body or body.startswith("#"):
        return None

    edit = rng.choice(("delete-token", "duplicate-token", "swap-tokens", "delete-char", "insert"))
    if edit == "delete-char":
        at = rng.randrange(len(line) - len(line.lstrip()), len(line))
        return line[:at] + line[at + 1 :], edit
    if edit == "insert":
        at = rng.randrange(len(line) - len(line.lstrip()), len(line) + 1)
        return line[:at] + rng.choice(OPERATORS) + line[at:], edit

    pieces = line_tokens(line)
    if pieces is None:
        return None
    if edit == "delete-token":
        return line.replace(rng.choice(pieces), "", 1), edit
    if edit == "duplicate-token":
        chosen = rng.choice(pieces)
        return line.replace(chosen, f"{chosen} {chosen}", 1), edit
    if len(pieces) < 2:
        return None
    first = rng.randrange(len(pieces) - 1)
    a, b = pieces[first], pieces[first + 1]
    if a == b:
        return None
    return line.replace(f"{a}{b}", f"{b}{a}", 1).replace(f"{a} {b}", f"{b} {a}", 1), edit


def mutate(path: Path, rng: random.Random) -> tuple[str, str, int] | None:
    """A broken version of `path`, or `None` if this attempt did not break it.

    An attempt fails more often than it looks like it should. Most edits to
    most lines produce a file that still parses, because deleting a name or
    duplicating one leaves a program that is wrong in meaning rather than in
    syntax, and this corpus is about refusals. Rather than hunt for a line that
    works, the caller tries again with a different file, which keeps the
    distribution of what gets broken closer to the distribution of real code.
    """
    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = original.splitlines(keepends=True)
    if not lines:
        return None

    at = rng.randrange(len(lines))
    broken = break_line(lines[at], rng)
    if broken is None:
        return None
    replacement, edit = broken
    if replacement == lines[at]:
        return None

    source = "".join([*lines[:at], replacement, *lines[at + 1 :]])
    if not refused(source, str(path)):
        return None
    return source, edit, at + 1


def refused(source: str, filename: str) -> bool:
    """Whether CPython will not compile this.

    Everything is caught rather than `SyntaxError` alone, for the same reason
    the errors differential does it: a bad escape in a format spec comes back
    as a `UnicodeDecodeError` and a null byte was a `ValueError` until 3.14.
    A refusal is a refusal whatever class it arrives as.
    """
    try:
        compile(source, filename, "exec")
    except Exception:
        return True
    return False


def generate(
    root: Path,
    *,
    count: int,
    seed: int,
    smallest: int = 8,
    largest: int = 400,
) -> list[Mutant]:
    """`count` broken files derived from the modules under `root`.

    Deterministic given the same seed and the same standard library. The second
    half of that is not a small caveat: a different Python version ships
    different modules, so two machines agree on the corpus only when they agree
    on the interpreter. The percentages this produces are comparable across
    runs on one machine and across machines running the same Python, which is
    what a floor in CI needs.
    """
    pool = sources(root, smallest=smallest, largest=largest)
    if not pool:
        return []

    rng = random.Random(seed)
    mutants: list[Mutant] = []
    # Bounded rather than looping until `count` is reached, because most
    # attempts fail and a pathological standard library would otherwise hang.
    for _ in range(count * 40):
        if len(mutants) == count:
            break
        path = rng.choice(pool)
        made = mutate(path, rng)
        if made is None:
            continue
        source, edit, line = made
        mutants.append(
            Mutant(
                name=f"m{len(mutants):05d}.py",
                source=source,
                origin=path.name,
                edit=edit,
                line=line,
            )
        )
    return mutants


def write(mutants: list[Mutant], into: Path) -> list[Path]:
    """Write the corpus out and return the paths, in order.

    Where each file came from goes in an index beside them rather than into a
    comment at the top of each one. A comment would be tidier to read and would
    also be a change to the file: prepending a line pushes a coding cookie off
    the first two lines of a module that has one, and then the mutant is not
    the file that was checked against CPython. The bytes written here are the
    bytes `mutate` decided were refused.
    """
    into.mkdir(parents=True, exist_ok=True)
    written = []
    index = []
    for mutant in mutants:
        path = into / mutant.name
        path.write_text(mutant.source, encoding="utf-8")
        index.append(f"{mutant.name}\t{mutant.origin}\tline {mutant.line}\t{mutant.edit}")
        written.append(path)
    (into / "index.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    return written
