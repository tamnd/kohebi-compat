"""What a comparison over a corpus of files is made of.

Two differentials share this: `tokens` compares against CPython's `tokenize`
module and `trees` compares against `ast.dump`. What they have in common is
everything except the comparison itself. The same set of outcomes, the same
notion of a file we chose not to look at and why, the same second oracle when
the first one refuses a file, and the same way of finding the corpus and the
binary to run over it.

Keeping that in one place is not only about repetition. An outcome that means
one thing in one differential and something slightly different in the other is
how a compatibility number quietly stops being comparable with itself.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import sysconfig
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatch
from pathlib import Path

Guard = Callable[[tuple[int, ...]], bool]
"""Whether an exclusion applies, given the version of the oracle."""


class FileOutcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNSUPPORTED = "unsupported"
    """kohebi said so itself, so it is a known gap and not a wrong answer."""
    FALSE_REJECT = "false-reject"
    """We refused a file CPython reads. Always a bug."""
    FALSE_ACCEPT = "false-accept"
    """We read a file CPython refuses. Always a bug."""
    WRONG_MESSAGE = "wrong-message"
    """Both refused it, and we did not say what CPython says."""
    EXCLUDED = "excluded"
    UNREADABLE = "unreadable"
    """Gone from disk between the listing and the read.

    A file that is not UTF-8 is not unreadable. It either declares what it is
    and both sides decode it, or it declares nothing and both sides refuse it
    with the same message.
    """


@dataclass(frozen=True, slots=True)
class FileResult:
    path: Path
    outcome: FileOutcome
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.outcome in (
            FileOutcome.MATCH,
            FileOutcome.UNSUPPORTED,
            FileOutcome.EXCLUDED,
            FileOutcome.UNREADABLE,
        )


@dataclass(frozen=True, slots=True)
class Failure:
    """What CPython did with a file it would not accept."""

    kind: str
    """`SyntaxError`, `IndentationError` or `TabError`."""
    message: str


def failure_from_report(report: str) -> Failure:
    """Pull the class and message out of a CPython shaped traceback.

    The last non-empty line is `SyntaxError: invalid syntax`, in exactly the
    form the interpreter prints, which is the form we are trying to match.
    """
    lines = [line for line in report.splitlines() if line.strip()]
    if not lines:
        return Failure("SyntaxError", "")
    kind, _, message = lines[-1].partition(": ")
    return Failure(kind.strip(), message.strip())


def compiler_verdict(source: bytes) -> Failure | None:
    """What `compile` says about this source, if it refuses it.

    The compiler is the second oracle and on error messages it is the one that
    counts, because its wording is what a user sees in a traceback. It is also
    stricter than the `tokenize` module in at least one place: `tokenize`
    happily returns a NAME for an identifier made of characters Python does not
    allow in one, and only the compiler says "invalid character".

    `ast.parse` goes through the same code and gives the same words, so the
    tree differential asks this too rather than keeping a second copy of the
    question.
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


class Exclusions:
    """Files we do not compare, each with a reason.

    Format is one rule per line, `<glob>: <reason>`, matched against the path
    as written. Blank lines and lines starting with `#` are ignored.

    A rule may carry a version guard, written `<glob> [python<3.14]: <reason>`,
    and then it only applies when the oracle is that old. Python changes its own
    error messages between releases, and kohebi reproduces one release, so a
    file that matches on 3.14 and not on 3.13 is a fact about CPython rather
    than about kohebi. Without the guard the choice would be to drop the file
    everywhere or to compare against only one version, and both of those are
    worse. `<` and `>=` are the two comparisons, which is enough to say "before
    this release" and "from this release on".

    The reason is not decoration. An exclusion saying "we do not support this
    yet" is fine and an exclusion with no reason is how a compatibility number
    stops meaning anything, so the parser refuses a rule without one.
    """

    def __init__(
        self,
        rules: Sequence[tuple[str, str]] = (),
        *,
        version: tuple[int, ...] | None = None,
    ) -> None:
        self.rules: list[tuple[str, str, Guard | None]] = [
            (glob, reason, None) for glob, reason in rules
        ]
        self.version = version or sys.version_info[:2]

    @classmethod
    def load(cls, path: Path | None, *, version: tuple[int, ...] | None = None) -> Exclusions:
        loaded = cls(version=version)
        if path is None or not path.exists():
            return loaded
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            head, sep, reason = line.partition(":")
            if not sep or not reason.strip():
                raise ValueError(f"{path}:{number}: exclusion has no reason: {line!r}")
            try:
                glob, guard = _split_guard(head.strip())
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
            loaded.rules.append((glob, reason.strip(), guard))
        return loaded

    def reason_for(self, path: Path) -> str | None:
        text = path.as_posix()
        for glob, reason, guard in self.rules:
            if not (fnmatch(text, glob) or fnmatch(path.name, glob)):
                continue
            if guard is not None and not guard(self.version):
                continue
            return reason
        return None


_GUARD = re.compile(r"^(?P<glob>.*?)\s*\[python\s*(?P<op><|>=)\s*(?P<version>\d+(?:\.\d+)*)\]$")


def _split_guard(head: str) -> tuple[str, Guard | None]:
    """Pull an optional `[python<3.14]` off the end of a rule's glob."""
    if not head.endswith("]"):
        return head, None
    found = _GUARD.match(head)
    if found is None:
        raise ValueError(f"exclusion has a guard it cannot read: {head!r}")
    wanted = tuple(int(part) for part in found["version"].split("."))
    if found["op"] == "<":
        return found["glob"], lambda running: running < wanted
    return found["glob"], lambda running: running >= wanted


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
