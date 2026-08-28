"""Differential testing of kohebi's parser against CPython's `ast` module.

The tokenizer differential next door compares one stage. This compares the
next one, and it is the stage that matters more, because everything after the
parser reads the tree rather than the tokens. A token stream that agrees and a
tree that does not is a bug that would otherwise reach the interpreter before
anyone noticed.

The oracle is `ast.dump(ast.parse(source), include_attributes=True)`, compared
as text. Comparing text rather than walking two trees sounds lazy and is not:
`ast.dump` is CPython's own printer, kohebi implements the same printer
character for character, and any field either side fills in wrongly shows up
without anyone writing an expected tree by hand. What it costs is that the
first difference is reported as a position in a long line, so the difference is
narrowed down to the smallest node that contains it before it is reported.

Attributes are included on purpose. A tree that agrees on shape and disagrees
on positions is a tree that will draw someone's error squiggle in the wrong
place, and the shape is the half that is easy to get right.

For a file that does not parse the oracle is the same one the tokenizer
differential uses, which is `compile`, because the message a user sees comes
from the compiler.
"""

from __future__ import annotations

import ast
import subprocess
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kohebi_compat.corpus import (
    Exclusions,
    Failure,
    FileOutcome,
    FileResult,
    compiler_verdict,
    failure_from_report,
)


def kohebi_tree(source: bytes, *, kohebi: Sequence[str]) -> str | Failure:
    """Ask the kohebi binary for the tree, in `ast.dump` form."""
    proc = subprocess.run(
        [*kohebi, "ast", "--format", "attributes", "-"],
        input=source,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout.decode().rstrip("\n")
    return failure_from_report(proc.stderr.decode("utf-8", "replace"))


def cpython_tree(source: bytes) -> str | Failure:
    """The same tree from CPython, printed by its own printer.

    Bytes rather than text, because `ast.parse` on bytes is the thing that
    honours a `# coding:` declaration, and deciding what encoding a file is in
    is part of what is being compared.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return compiler_verdict(source) or Failure(type(exc).__name__, exc.msg or str(exc))
    except ValueError as exc:
        # A null byte, which `ast.parse` refuses before it parses anything.
        return Failure("SyntaxError", str(exc))
    except (MemoryError, RecursionError) as exc:
        return Failure(type(exc).__name__, str(exc))
    return ast.dump(tree, include_attributes=True)


def compare_source(source: str, *, kohebi: Sequence[str]) -> FileResult:
    """Compare the two parsers on one piece of source text."""
    return _compare(Path("<string>"), source.encode("utf-8"), kohebi=kohebi)


def compare_file(path: Path, *, kohebi: Sequence[str]) -> FileResult:
    try:
        source = path.read_bytes()
    except OSError as exc:
        return FileResult(path, FileOutcome.UNREADABLE, str(exc))
    return _compare(path, source, kohebi=kohebi)


def _compare(path: Path, source: bytes, *, kohebi: Sequence[str]) -> FileResult:
    ours = kohebi_tree(source, kohebi=kohebi)
    theirs = cpython_tree(source)

    if isinstance(ours, Failure) and ours.kind == "NotImplementedError":
        # kohebi saying this is a gap in kohebi rather than a problem with the
        # file. An honest gap is not a wrong answer, and it still counts
        # against agreement, which is the number that says how much works.
        return FileResult(path, FileOutcome.UNSUPPORTED, ours.message)

    match (isinstance(ours, Failure), isinstance(theirs, Failure)):
        case (False, False):
            assert isinstance(ours, str)
            assert isinstance(theirs, str)
            if ours == theirs:
                return FileResult(path, FileOutcome.MATCH)
            return FileResult(path, FileOutcome.MISMATCH, first_difference(ours, theirs))
        case (True, False):
            assert isinstance(ours, Failure)
            return FileResult(
                path,
                FileOutcome.FALSE_REJECT,
                f"we said {ours.kind}: {ours.message}",
            )
        case (False, True):
            assert isinstance(theirs, Failure)
            return FileResult(
                path,
                FileOutcome.FALSE_ACCEPT,
                f"CPython said {theirs.kind}: {theirs.message}",
            )
        case _:
            assert isinstance(ours, Failure)
            assert isinstance(theirs, Failure)
            if (ours.kind, ours.message) == (theirs.kind, theirs.message):
                return FileResult(path, FileOutcome.MATCH)
            return FileResult(
                path,
                FileOutcome.WRONG_MESSAGE,
                f"{ours.kind}: {ours.message!r} vs {theirs.kind}: {theirs.message!r}",
            )


def first_difference(ours: str, theirs: str, *, window: int = 60) -> str:
    """Where two dumps stop agreeing, said in a way someone can act on.

    A dump of a real module is tens of thousands of characters on one line, so
    the offset on its own is useless and the whole line is worse. What helps is
    the smallest node that contains the difference, which is found by walking
    back to the last unclosed `(` before the split and reading its name.
    """
    at = _split(ours, theirs)
    node = _enclosing_node(theirs[:at]) or _enclosing_node(ours[:at]) or "the tree"
    return (
        f"in {node} at character {at}: "
        f"we wrote {ours[at : at + window]!r}, CPython wrote {theirs[at : at + window]!r}"
    )


def _split(ours: str, theirs: str) -> int:
    for i, (mine, yours) in enumerate(zip(ours, theirs, strict=False)):
        if mine != yours:
            return i
    return min(len(ours), len(theirs))


def _enclosing_node(text: str) -> str | None:
    """The name of the innermost node still open at the end of `text`."""
    depth = 0
    quote: str | None = None
    escaped = False
    opens: list[int] = []
    for i, ch in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "(":
            opens.append(i)
            depth += 1
        elif ch == ")" and depth:
            opens.pop()
            depth -= 1
    if not opens:
        return None
    end = opens[-1]
    start = end
    while start and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    name = text[start:end]
    return name or None


def run(
    paths: Sequence[Path],
    *,
    kohebi: Sequence[str],
    exclusions: Exclusions,
    jobs: int = 8,
) -> Iterator[FileResult]:
    """Compare every file, in the order given, with `jobs` running at once."""

    def one(path: Path) -> FileResult:
        reason = exclusions.reason_for(path)
        if reason is not None:
            return FileResult(path, FileOutcome.EXCLUDED, reason)
        return compare_file(path, kohebi=kohebi)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        yield from pool.map(one, paths)
