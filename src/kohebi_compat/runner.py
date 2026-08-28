"""The differential runner.

The correctness claim for kohebi is "matches CPython". That gives us an
executable oracle: for any program, CPython's behaviour is the right answer and
disagreement is a bug by definition. Almost everything here follows from taking
that seriously.

Three configurations run the same program and must agree:

    CPython 3.x        the oracle
    kohebi run         JIT mode
    kohebi build       AOT mode

Two-way disagreements are informative in themselves. CPython and `kohebi run`
agreeing while `kohebi build` differs means the AOT compiler is wrong. Both
kohebi modes agreeing against CPython means the shared frontend is wrong.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .normalize import STRICT, Normalisation, normalise


class Outcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    ORACLE_FAILED = "oracle-failed"
    TIMEOUT = "timeout"
    NOT_INSTALLED = "not-installed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Interpreter:
    """One thing that can run a Python file."""

    name: str
    argv: tuple[str, ...]
    """Command prefix. The script path is appended."""

    def available(self) -> bool:
        return shutil.which(self.argv[0]) is not None

    def version(self) -> str:
        if not self.available():
            return "not installed"
        try:
            proc = subprocess.run(
                [*self.argv, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"
        return (
            (proc.stdout or proc.stderr).strip().splitlines()[0]
            if (proc.stdout or proc.stderr)
            else "unknown"
        )


CPYTHON = Interpreter("cpython", ("python3",))
KOHEBI_RUN = Interpreter("kohebi-run", ("kohebi", "run"))
KOHEBI_BUILD = Interpreter("kohebi-build", ("kohebi", "build", "--run"))
PYPY = Interpreter("pypy", ("pypy3",))
GRAALPY = Interpreter("graalpy", ("graalpy",))


@dataclass(frozen=True, slots=True)
class Execution:
    """What one interpreter did with one program."""

    interpreter: str
    returncode: int
    stdout: bytes
    stderr: bytes
    duration_s: float
    timed_out: bool = False

    def key(self, how: Normalisation) -> tuple[int, bytes, bytes]:
        """The tuple that gets compared. Anything not in here is ignored."""
        return (
            self.returncode,
            normalise(self.stdout, how),
            normalise(self.stderr, how),
        )

    def differences(self, other: Execution, how: Normalisation) -> list[str]:
        """Which fields differ, and the first line on which they do.

        A report saying only that PyPy disagreed is a report nobody acts on.
        This is what makes a mismatch into something someone can open.
        """
        if self.timed_out or other.timed_out:
            return ["timed out"]
        out = []
        if self.returncode != other.returncode:
            out.append(f"exit {self.returncode} vs {other.returncode}")
        for field_name in ("stdout", "stderr"):
            mine = normalise(getattr(self, field_name), how)
            theirs = normalise(getattr(other, field_name), how)
            if mine != theirs:
                out.append(f"{field_name}: {_first_difference(mine, theirs)}")
        return out


@dataclass(slots=True)
class Result:
    case: str
    outcome: Outcome
    oracle: Execution | None = None
    others: dict[str, Execution] = field(default_factory=dict)
    disagreed: list[str] = field(default_factory=list)
    detail: dict[str, list[str]] = field(default_factory=dict)
    """Per interpreter, what actually differed. Keyed by interpreter name."""
    note: str = ""

    @property
    def passed(self) -> bool:
        return self.outcome in (Outcome.MATCH, Outcome.SKIPPED)


def execute(
    interpreter: Interpreter,
    script: Path,
    *,
    timeout_s: float = 60.0,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> Execution:
    """Run one program under one interpreter, capturing everything."""
    full_env = {
        **os.environ,
        "PYTHONHASHSEED": "0",
        # The suite compares bytes, so the encoding cannot be left to the
        # platform. Windows defaults the console to cp1252, which cannot encode
        # most of what string_and_unicode.py prints, so the oracle itself died
        # with UnicodeEncodeError and the case was unrunnable on that platform.
        "PYTHONIOENCODING": "utf-8",
        **(env or {}),
    }
    # Absolute, because cwd is a scratch directory the case can write into and
    # a relative path would be resolved against that instead. When this was
    # relative, no case ever ran: every interpreter reported "can't open file"
    # and the suite compared those failures to each other and called it a match.
    target = str(script.resolve())
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [*interpreter.argv, target],
            capture_output=True,
            timeout=timeout_s,
            cwd=cwd,
            env=full_env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return Execution(
            interpreter=interpreter.name,
            returncode=-1,
            stdout=exc.stdout or b"",
            stderr=exc.stderr or b"",
            duration_s=time.perf_counter() - started,
            timed_out=True,
        )
    return Execution(
        interpreter=interpreter.name,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_s=time.perf_counter() - started,
    )


def compare(
    script: Path,
    *,
    oracle: Interpreter = CPYTHON,
    against: Sequence[Interpreter] = (KOHEBI_RUN, KOHEBI_BUILD),
    how: Normalisation = STRICT,
    timeout_s: float = 60.0,
) -> Result:
    """Run one case under the oracle and everything else, and compare."""
    name = script.name

    if not oracle.available():
        return Result(name, Outcome.NOT_INSTALLED, note=f"oracle {oracle.name} missing")

    with tempfile.TemporaryDirectory(prefix="kohebi-compat-") as tmp:
        cwd = Path(tmp)
        oracle_run = execute(oracle, script, timeout_s=timeout_s, cwd=cwd)

        if oracle_run.timed_out:
            return Result(name, Outcome.TIMEOUT, oracle=oracle_run, note="oracle timed out")

        # A case is expected to run to completion under the oracle. If it does
        # not, there is no correct answer to compare anything against, and
        # calling that a match is how a suite reports green while running
        # nothing. That is not hypothetical: it is what this suite did until
        # the script path was made absolute.
        if oracle_run.returncode != 0:
            err = oracle_run.stderr.decode("utf-8", "replace").strip().splitlines()
            why = err[-1] if err else "no stderr"
            return Result(
                name,
                Outcome.ORACLE_FAILED,
                oracle=oracle_run,
                note=f"oracle exited {oracle_run.returncode}: {why}",
            )

        result = Result(name, Outcome.MATCH, oracle=oracle_run)
        expected = oracle_run.key(how)

        for interp in against:
            if not interp.available():
                result.others[interp.name] = Execution(interp.name, -1, b"", b"", 0.0)
                continue
            got = execute(interp, script, timeout_s=timeout_s, cwd=cwd)
            result.others[interp.name] = got
            if got.timed_out or got.key(how) != expected:
                result.disagreed.append(interp.name)
                result.detail[interp.name] = oracle_run.differences(got, how)

        if result.disagreed:
            result.outcome = Outcome.MISMATCH
        return result


def collect(root: Path) -> list[Path]:
    """Every `.py` file under `root`, in a stable order.

    Files whose name starts with an underscore are helpers, not cases.
    """
    return sorted(p for p in root.rglob("*.py") if not p.name.startswith("_"))


def _first_difference(a: bytes, b: bytes, *, width: int = 90) -> str:
    """Describe where two outputs first diverge, in one readable line."""
    left = a.decode("utf-8", "replace").splitlines()
    right = b.decode("utf-8", "replace").splitlines()
    for i, (x, y) in enumerate(zip(left, right, strict=False), start=1):
        if x != y:
            return f"line {i}, {x[:width]!r} vs {y[:width]!r}"
    if len(left) != len(right):
        longer, which = (left, "oracle") if len(left) > len(right) else (right, "candidate")
        extra = longer[min(len(left), len(right))][:width]
        return f"{which} has {abs(len(left) - len(right))} extra line(s), first {extra!r}"
    return "differs only in trailing bytes"
