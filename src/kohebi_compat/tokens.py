"""Differential testing of kohebi's lexer against CPython's `tokenize` module.

The suite next door compares whole programs by running them. That is the right
end goal and it is useless right now, because kohebi cannot run a program yet
and will not be able to for a while. Waiting until it can means finding out
about a frontend bug months after writing it.

So this compares one stage instead. CPython ships a tokenizer written in Python
that anyone can point at any file, which turns every `.py` file on the machine
into a test case nobody had to write. The default corpus is the standard
library of the oracle interpreter, which is a few thousand files of real code
written by many hands over thirty years, and it finds things a hand written
suite does not.

Two oracles, not one, and the difference matters:

- For a file that tokenizes, the oracle is `tokenize.generate_tokens`, and we
  compare the token streams element for element.
- For a file that does not, the oracle is `compile`, because the error messages
  kohebi is trying to reproduce are the compiler's, not the `tokenize` module's.
  `tokenize` says "unterminated string literal" in its own words and the words
  a user actually sees come from the compiler.

Comparison goes through the JSON form of `kohebi tokenize` rather than the
human one, so that the two sides never have to agree on a quoting convention.
"""

from __future__ import annotations

import io
import json
import subprocess
import tokenize
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

Tok = tuple[str, tuple[int, int], tuple[int, int], str]
"""One token as `(type, start, end, text)`, in `tokenize` module terms."""


def kohebi_tokens(source: bytes, *, kohebi: Sequence[str]) -> list[Tok] | Failure:
    """Ask the kohebi binary to tokenize `source`.

    Bytes rather than text, because deciding what encoding those bytes are in
    is part of what is being compared. A file says so itself, in a comment on
    its first or second line, and kohebi has to reach the same answer CPython
    does before either of them has a token to show for it.
    """
    proc = subprocess.run(
        [*kohebi, "tokenize", "--format", "json", "-"],
        input=source,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return [_from_json(line) for line in proc.stdout.decode().splitlines()]
    return failure_from_report(proc.stderr.decode("utf-8", "replace"))


def _from_json(line: str) -> Tok:
    obj = json.loads(line)
    return (
        obj["type"],
        (obj["start"][0], obj["start"][1]),
        (obj["end"][0], obj["end"][1]),
        obj["text"],
    )


def cpython_tokens(source: bytes) -> list[Tok] | Failure:
    """Tokenize with CPython, falling back to `compile` for the message.

    Decoding comes first and is its own way to fail. A file that declares an
    encoding it does not have, or that is not UTF-8 and declares nothing, never
    reaches a tokenizer at all, and what a user sees is the compiler's
    complaint about the bytes.

    A file that `tokenize` rejects gets handed to `compile` for the same
    reason: the two disagree about wording and the compiler's wording is the
    one users see and the one kohebi reproduces. If `compile` somehow accepts
    it, the `tokenize` error stands, since something has to be reported.
    """
    try:
        text = decode(source)
    except (SyntaxError, UnicodeDecodeError, LookupError) as exc:
        return compiler_verdict(source) or Failure("SyntaxError", str(exc))
    try:
        readline = io.StringIO(text).readline
        return [
            (tokenize.tok_name[t.type], t.start, t.end, t.string)
            for t in tokenize.generate_tokens(readline)
        ]
    except (SyntaxError, tokenize.TokenError) as exc:
        return compiler_verdict(source) or Failure(type(exc).__name__, str(exc))


def decode(source: bytes) -> str:
    """The text of a file, in whatever encoding it says it is in.

    `detect_encoding` is a third oracle and it is not quite the one the
    compiler uses, so a disagreement between them shows up as a decode that
    fails here and a `compile` that succeeds, or the other way round. Over the
    standard library they agree on every file. The byte order mark is dropped
    rather than kept, because it is not part of the program and reading it as a
    character makes the first token of every such file wrong.
    """
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    return source.decode(encoding)


def compare_source(source: str, *, kohebi: Sequence[str]) -> FileResult:
    """Compare the two tokenizers on one piece of source text."""
    return _compare(Path("<string>"), source.encode("utf-8"), kohebi=kohebi)


def _compare(path: Path, source: bytes, *, kohebi: Sequence[str]) -> FileResult:
    ours = kohebi_tokens(source, kohebi=kohebi)
    theirs = cpython_tokens(source)

    if isinstance(ours, Failure) and ours.kind == "NotImplementedError":
        # kohebi is telling us this is a gap in kohebi rather than a problem
        # with the file. f-strings are the whole of this today.
        return FileResult(path, FileOutcome.UNSUPPORTED, ours.message)

    match (isinstance(ours, Failure), isinstance(theirs, Failure)):
        case (False, False):
            assert not isinstance(ours, Failure)
            assert not isinstance(theirs, Failure)
            difference = _first_difference(ours, theirs)
            if difference is None:
                return FileResult(path, FileOutcome.MATCH)
            return FileResult(path, FileOutcome.MISMATCH, difference)
        case (True, False):
            assert isinstance(ours, Failure)
            # `tokenize` accepted it, but `tokenize` is not the last word. Ask
            # the compiler before calling this a wrong answer.
            verdict = compiler_verdict(source)
            if verdict is None:
                return FileResult(
                    path,
                    FileOutcome.FALSE_REJECT,
                    f"we said {ours.kind}: {ours.message}",
                )
            if (ours.kind, ours.message) == (verdict.kind, verdict.message):
                return FileResult(path, FileOutcome.MATCH)
            return FileResult(
                path,
                FileOutcome.WRONG_MESSAGE,
                f"{ours.kind}: {ours.message!r} vs {verdict.kind}: {verdict.message!r}",
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


def _first_difference(ours: list[Tok], theirs: list[Tok]) -> str | None:
    """The first token that differs, described so someone can act on it."""
    for i, (mine, yours) in enumerate(zip(ours, theirs, strict=False)):
        if mine != yours:
            return f"token {i}: {_show(mine)} vs CPython {_show(yours)}"
    if len(ours) < len(theirs):
        return f"we stopped after {len(ours)} tokens, CPython went on to {_show(theirs[len(ours)])}"
    if len(ours) > len(theirs):
        return (
            f"we emitted {_show(ours[len(theirs)])} after CPython finished at {len(theirs)} tokens"
        )
    return None


def _show(tok: Tok) -> str:
    kind, start, end, text = tok
    return f"{kind} {start[0]},{start[1]}-{end[0]},{end[1]} {text!r}"


def compare_file(path: Path, *, kohebi: Sequence[str]) -> FileResult:
    try:
        source = path.read_bytes()
    except OSError as exc:
        # Gone from disk between the listing and the read, which happens on a
        # machine that is doing anything else at the same time.
        return FileResult(path, FileOutcome.UNREADABLE, str(exc))
    return _compare(path, source, kohebi=kohebi)


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
