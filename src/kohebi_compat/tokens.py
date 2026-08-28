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
import shutil
import subprocess
import sys
import sysconfig
import tokenize
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatch
from pathlib import Path

Tok = tuple[str, tuple[int, int], tuple[int, int], str]
"""One token as `(type, start, end, text)`, in `tokenize` module terms."""


class TokenOutcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNSUPPORTED = "unsupported"
    """kohebi said so itself, so it is a known gap and not a wrong answer."""
    FALSE_REJECT = "false-reject"
    """We refused a file CPython tokenizes. Always a bug."""
    FALSE_ACCEPT = "false-accept"
    """We tokenized a file CPython refuses. Always a bug."""
    WRONG_MESSAGE = "wrong-message"
    """Both refused it, and we did not say what CPython says."""
    EXCLUDED = "excluded"
    UNREADABLE = "unreadable"
    """Not valid UTF-8, or gone from disk between listing and reading."""


@dataclass(frozen=True, slots=True)
class TokenResult:
    path: Path
    outcome: TokenOutcome
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.outcome in (
            TokenOutcome.MATCH,
            TokenOutcome.UNSUPPORTED,
            TokenOutcome.EXCLUDED,
            TokenOutcome.UNREADABLE,
        )


@dataclass(frozen=True, slots=True)
class Failure:
    """What CPython did with a file it would not accept."""

    kind: str
    """`SyntaxError`, `IndentationError` or `TabError`."""
    message: str


def kohebi_tokens(source: str, *, kohebi: Sequence[str]) -> list[Tok] | Failure:
    """Ask the kohebi binary to tokenize `source`."""
    proc = subprocess.run(
        [*kohebi, "tokenize", "--format", "json", "-"],
        input=source.encode(),
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return [_from_json(line) for line in proc.stdout.decode().splitlines()]
    return _failure_from_report(proc.stderr.decode("utf-8", "replace"))


def _from_json(line: str) -> Tok:
    obj = json.loads(line)
    return (
        obj["type"],
        (obj["start"][0], obj["start"][1]),
        (obj["end"][0], obj["end"][1]),
        obj["text"],
    )


def _failure_from_report(report: str) -> Failure:
    """Pull the class and message out of a CPython shaped traceback.

    The last non-empty line is `SyntaxError: invalid syntax`, in exactly the
    form the interpreter prints, which is the form we are trying to match.
    """
    lines = [line for line in report.splitlines() if line.strip()]
    if not lines:
        return Failure("SyntaxError", "")
    kind, _, message = lines[-1].partition(": ")
    return Failure(kind.strip(), message.strip())


def cpython_tokens(source: str) -> list[Tok] | Failure:
    """Tokenize with CPython, falling back to `compile` for the message.

    A file that `tokenize` rejects gets handed to `compile`, because the two
    disagree about wording and the compiler's wording is the one users see and
    the one kohebi reproduces. If `compile` somehow accepts it, the `tokenize`
    error stands, since something has to be reported.
    """
    try:
        readline = io.StringIO(source).readline
        return [
            (tokenize.tok_name[t.type], t.start, t.end, t.string)
            for t in tokenize.generate_tokens(readline)
        ]
    except (SyntaxError, tokenize.TokenError) as exc:
        return compiler_verdict(source) or Failure(type(exc).__name__, str(exc))


def compiler_verdict(source: str) -> Failure | None:
    """What `compile` says about this source, if it refuses it.

    The compiler is the second oracle and on error messages it is the one that
    counts, because its wording is what a user sees in a traceback. It is also
    stricter than the `tokenize` module in at least one place: `tokenize`
    happily returns a NAME for an identifier made of characters Python does not
    allow in one, and only the compiler says "invalid character".
    """
    try:
        compile(source, "<corpus>", "exec")
    except SyntaxError as exc:
        # `.msg` rather than `str(exc)`, which appends " (file, line N)".
        # Stripping that off by hand cuts "invalid character '\u20ac' (U+20AC)"
        # at the wrong parenthesis. The message alone is what kohebi prints on
        # its last line, so the message alone is what we compare.
        return Failure(type(exc).__name__, exc.msg or str(exc))
    except ValueError as exc:
        # Source containing a null byte, which `compile` rejects before it
        # parses anything.
        return Failure("SyntaxError", str(exc))
    except (MemoryError, RecursionError) as exc:
        return Failure(type(exc).__name__, str(exc))
    return None


def compare_source(source: str, *, kohebi: Sequence[str]) -> TokenResult:
    """Compare the two tokenizers on one piece of source text."""
    return _compare(Path("<string>"), source, kohebi=kohebi)


def _compare(path: Path, source: str, *, kohebi: Sequence[str]) -> TokenResult:
    ours = kohebi_tokens(source, kohebi=kohebi)
    theirs = cpython_tokens(source)

    if isinstance(ours, Failure) and ours.kind == "NotImplementedError":
        # kohebi is telling us this is a gap in kohebi rather than a problem
        # with the file. f-strings are the whole of this today.
        return TokenResult(path, TokenOutcome.UNSUPPORTED, ours.message)

    match (isinstance(ours, Failure), isinstance(theirs, Failure)):
        case (False, False):
            assert not isinstance(ours, Failure)
            assert not isinstance(theirs, Failure)
            difference = _first_difference(ours, theirs)
            if difference is None:
                return TokenResult(path, TokenOutcome.MATCH)
            return TokenResult(path, TokenOutcome.MISMATCH, difference)
        case (True, False):
            assert isinstance(ours, Failure)
            # `tokenize` accepted it, but `tokenize` is not the last word. Ask
            # the compiler before calling this a wrong answer.
            verdict = compiler_verdict(source)
            if verdict is None:
                return TokenResult(
                    path,
                    TokenOutcome.FALSE_REJECT,
                    f"we said {ours.kind}: {ours.message}",
                )
            if (ours.kind, ours.message) == (verdict.kind, verdict.message):
                return TokenResult(path, TokenOutcome.MATCH)
            return TokenResult(
                path,
                TokenOutcome.WRONG_MESSAGE,
                f"{ours.kind}: {ours.message!r} vs {verdict.kind}: {verdict.message!r}",
            )
        case (False, True):
            assert isinstance(theirs, Failure)
            return TokenResult(
                path,
                TokenOutcome.FALSE_ACCEPT,
                f"CPython said {theirs.kind}: {theirs.message}",
            )
        case _:
            assert isinstance(ours, Failure)
            assert isinstance(theirs, Failure)
            if (ours.kind, ours.message) == (theirs.kind, theirs.message):
                return TokenResult(path, TokenOutcome.MATCH)
            return TokenResult(
                path,
                TokenOutcome.WRONG_MESSAGE,
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


def compare_file(path: Path, *, kohebi: Sequence[str]) -> TokenResult:
    try:
        # utf-8-sig, not utf-8. A byte order mark is not part of the program,
        # and CPython strips it while decoding the file. Reading it as a
        # character instead makes the first token of every such file wrong for
        # reasons that have nothing to do with either tokenizer.
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        # A corpus taken off a real machine has files that are not UTF-8 on
        # purpose, because they are test data for the decoder.
        return TokenResult(path, TokenOutcome.UNREADABLE, str(exc))
    return _compare(path, source, kohebi=kohebi)


def run(
    paths: Sequence[Path],
    *,
    kohebi: Sequence[str],
    exclusions: Exclusions,
    jobs: int = 8,
) -> Iterator[TokenResult]:
    """Compare every file, in the order given, with `jobs` running at once."""

    def one(path: Path) -> TokenResult:
        reason = exclusions.reason_for(path)
        if reason is not None:
            return TokenResult(path, TokenOutcome.EXCLUDED, reason)
        return compare_file(path, kohebi=kohebi)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        yield from pool.map(one, paths)


class Exclusions:
    """Files we do not compare, each with a reason.

    Format is one rule per line, `<glob>: <reason>`, matched against the path
    as written. Blank lines and lines starting with `#` are ignored.

    The reason is not decoration. An exclusion saying "we do not support this
    yet" is fine and an exclusion with no reason is how a compatibility number
    stops meaning anything, so the parser refuses a rule without one.
    """

    def __init__(self, rules: Sequence[tuple[str, str]] = ()) -> None:
        self.rules = list(rules)

    @classmethod
    def load(cls, path: Path | None) -> Exclusions:
        if path is None or not path.exists():
            return cls()
        rules = []
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            glob, sep, reason = line.partition(":")
            if not sep or not reason.strip():
                raise ValueError(f"{path}:{number}: exclusion has no reason: {line!r}")
            rules.append((glob.strip(), reason.strip()))
        return cls(rules)

    def reason_for(self, path: Path) -> str | None:
        text = path.as_posix()
        for glob, reason in self.rules:
            if fnmatch(text, glob) or fnmatch(path.name, glob):
                return reason
        return None


def default_corpus(python: str | None = None) -> Path:
    """The standard library of the interpreter we are comparing against.

    A few thousand files of real Python written by many hands over thirty
    years, already on disk, already known to be valid.
    """
    if python is None or python == sys.executable:
        return Path(sysconfig.get_paths()["stdlib"])
    out = subprocess.run(
        [python, "-c", "import sysconfig; print(sysconfig.get_paths()['stdlib'])"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip())


def find_kohebi(explicit: str | None) -> list[str] | None:
    """Locate the kohebi binary, preferring a local debug build."""
    if explicit:
        return [explicit] if Path(explicit).exists() or shutil.which(explicit) else None
    found = shutil.which("kohebi")
    return [found] if found else None
