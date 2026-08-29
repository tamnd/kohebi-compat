"""Differential testing of what kohebi says about a file it will not accept.

The other two differentials compare a file both sides read. This one compares
a file neither side reads, which is a contract of its own and one the standard
library cannot exercise, because every file in it is valid. A corpus of
deliberately broken files is the only way to measure it.

What is compared is the whole block a person sees, meaning the `File` line, the
source line, the carets under it and the exception line, exactly as
`traceback.format_exception_only` prints it. Comparing the block rather than
the five fields is not a shortcut: the block is what someone reads, and it
covers the class, the message, the line and both columns in one comparison
with nothing to keep in step by hand.

It also catches something the five fields would hide. A `SyntaxError` can be
missing its filename, its line or its column, and the traceback module prints
as far down that list as it can get, so a refusal is four lines, or three, or
two, or one. A null byte is one. An unknown encoding is two. Getting the words
right and the shape wrong is still wrong, and only the block shows it.

Both sides are given the same filename, which is the path as written on the
command line, because the filename is part of the block and a comparison that
had to paper over it would be papering over the first line.

There is no expected output stored anywhere. CPython is the oracle at the time
the comparison runs, so adding a case is adding a file to the corpus, and a
message CPython changes in a future release shows up as a difference rather
than as a fixture nobody updated.
"""

from __future__ import annotations

import subprocess
import traceback
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kohebi_compat.corpus import Exclusions, FileOutcome, FileResult


def kohebi_report(path: Path, *, kohebi: Sequence[str]) -> str | None:
    """The block kohebi prints for this file, or `None` if it accepts it.

    The file is passed by name rather than on standard input, so that the name
    kohebi prints is the name CPython is given and the first line of the two
    blocks is comparable.

    `--compile` because the oracle below is `compile` and not `ast.parse`, and
    the two do not refuse the same files. `ast.parse` stops as soon as it has a
    tree, so it is perfectly happy with `f(a=1, a=2)`, and `compile` runs two
    more passes over that tree and throws it out. Without the flag every file
    in that family reads as a difference when it is only a difference in what
    was asked. The tree differential wants the other one and keeps using it.
    """
    proc = subprocess.run(
        [*kohebi, "ast", "--compile", str(path)],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode == 0:
        return None
    return proc.stderr.decode("utf-8", "replace").strip("\n")


def cpython_report(path: Path, source: bytes) -> str | None:
    """The same block from CPython, or `None` if it accepts the file.

    `compile` rather than `ast.parse`, because the wording a user sees comes
    from the compiler, and bytes rather than text, because deciding what
    encoding a file is in is part of what can go wrong.

    Everything is caught rather than `SyntaxError` alone. Not every way of
    writing a bad program gets one: a bad escape inside a format spec comes
    back as a bare `UnicodeDecodeError`, and a null byte was a `ValueError`
    until 3.14 made it a `SyntaxError`. `format_exception_only` prints all of
    them, as far down from the file to the carets as each one has the
    information for, which is what a user sees either way.
    """
    try:
        compile(source, str(path), "exec")
    except Exception as exc:
        return "".join(traceback.format_exception_only(type(exc), exc)).strip("\n")
    return None


def compare_file(path: Path, *, kohebi: Sequence[str]) -> FileResult:
    try:
        source = path.read_bytes()
    except OSError as exc:
        return FileResult(path, FileOutcome.UNREADABLE, str(exc))

    ours = kohebi_report(path, kohebi=kohebi)
    theirs = cpython_report(path, source)

    if ours is not None and ours.startswith("NotImplementedError"):
        # kohebi saying this is a gap in kohebi rather than a wrong answer. It
        # still counts against agreement, which is the number that says how
        # much works.
        return FileResult(path, FileOutcome.UNSUPPORTED, ours)

    if theirs is None:
        if ours is None:
            # Nothing to compare, and a file in this corpus that both sides
            # read is a mistake in the corpus rather than in either parser.
            return FileResult(
                path,
                FileOutcome.MISMATCH,
                "CPython reads this file, so it does not belong in a corpus of broken ones",
            )
        return FileResult(path, FileOutcome.FALSE_REJECT, f"we said {ours.splitlines()[-1]}")
    if ours is None:
        return FileResult(path, FileOutcome.FALSE_ACCEPT, f"CPython said {theirs.splitlines()[-1]}")
    if ours == theirs:
        return FileResult(path, FileOutcome.MATCH)
    return FileResult(path, FileOutcome.WRONG_MESSAGE, first_difference(ours, theirs))


def first_difference(ours: str, theirs: str) -> str:
    """The first line the two blocks disagree on, with both spellings of it.

    A block is at most four short lines, so quoting the pair that differs says
    the whole story. Quoting them with `repr` matters more than it looks: two
    lines of carets that differ in length are otherwise indistinguishable in a
    log. A block that is the wrong length has no differing pair, and the
    lengths are the report.
    """
    mine = ours.splitlines()
    yours = theirs.splitlines()
    for number, (a, b) in enumerate(zip(mine, yours, strict=False), start=1):
        if a != b:
            return f"line {number} of the report: we wrote {a!r}, CPython wrote {b!r}"
    return f"we printed {len(mine)} line(s) and CPython printed {len(yours)}"


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
