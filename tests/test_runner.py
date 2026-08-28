"""Tests for the harness itself.

A differential harness that cannot detect a difference is worse than no
harness, because it reports a green suite. The negative cases below matter more
than the positive ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from kohebi_compat import (
    CPYTHON,
    LENIENT,
    STRICT,
    Interpreter,
    Outcome,
    Result,
    collect,
    compare,
    execute,
    normalise,
)
from kohebi_compat.__main__ import main


@pytest.fixture
def script(tmp_path: Path):
    def make(body: str) -> Path:
        path = tmp_path / "case.py"
        path.write_text(body)
        return path

    return make


class TestNormalise:
    def test_addresses_are_erased(self):
        got = normalise(b"<obj at 0x7f3c8a0b1e50>")
        assert got == b"<obj at 0xADDR>"

    def test_paths_reduce_to_basename(self):
        got = normalise(b'  File "/tmp/xyz123/case.py", line 3')
        assert got == b'  File "case.py", line 3'

    def test_windows_paths_reduce_too(self):
        got = normalise(rb'File "C:\Users\x\case.py"')
        assert got == b'File "case.py"'

    def test_strict_keeps_traceback_detail(self):
        tb = b'Traceback:\n  File "a.py", line 1\nValueError: boom'
        assert b"line 1" in normalise(tb, STRICT)

    def test_lenient_keeps_only_the_exception(self):
        tb = b'Traceback:\n  File "a.py", line 1\nValueError: boom'
        assert normalise(tb, LENIENT) == b"ValueError: boom"

    def test_error_message_text_is_never_normalised(self):
        # Message text is a compatibility requirement, not noise.
        msg = b"TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        assert normalise(msg) == msg


class TestExecute:
    def test_captures_output_and_status(self, script):
        path = script("import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)")
        run = execute(CPYTHON, path)
        assert run.returncode == 3
        assert run.stdout.strip() == b"out"
        assert b"err" in run.stderr

    def test_timeout_is_reported_not_raised(self, script):
        path = script("import time; time.sleep(30)")
        run = execute(CPYTHON, path, timeout_s=0.5)
        assert run.timed_out


class TestCompare:
    def test_identical_interpreters_agree(self, script):
        path = script("print('hello')")
        result = compare(path, against=[CPYTHON])
        assert result.outcome is Outcome.MATCH
        assert result.passed

    def test_detects_a_stdout_difference(self, script):
        """The case that matters: a real divergence must not pass."""
        path = script("import sys; print(sys.argv[0].endswith('case.py'))")
        # An interpreter that prints something else entirely.
        liar = Interpreter("liar", (sys.executable, "-c", "print('nope');import sys;sys.exit(0)#"))
        result = compare(path, against=[liar])
        assert result.outcome is Outcome.MISMATCH
        assert "liar" in result.disagreed
        assert not result.passed

    def test_detects_an_exit_code_difference(self, script):
        path = script("raise SystemExit(0)")
        failing = Interpreter("failing", (sys.executable, "-c", "raise SystemExit(7)#"))
        result = compare(path, against=[failing])
        assert result.outcome is Outcome.MISMATCH

    def test_a_missing_interpreter_is_not_a_pass(self, script):
        """An interpreter that never ran cannot have agreed with the oracle.

        This used to return MATCH, which meant running the suite without
        kohebi installed, the situation everyone is in right now, printed a
        100% pass rate for a runtime that does not exist yet.
        """
        path = script("print(1)")
        absent = Interpreter("absent", ("definitely-not-a-real-binary-xyz",))
        result = compare(path, against=[absent])
        assert result.outcome is Outcome.NOT_INSTALLED
        assert not result.passed
        assert "absent" in result.note


class TestCollect:
    def test_finds_cases_in_order_and_skips_helpers(self, tmp_path: Path):
        (tmp_path / "b.py").touch()
        (tmp_path / "a.py").touch()
        (tmp_path / "_helper.py").touch()
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "c.py").touch()
        assert [p.name for p in collect(tmp_path)] == ["a.py", "b.py", "c.py"]


def test_the_shipped_suite_is_self_consistent():
    """Every case in suites/ must at minimum run under CPython."""
    suites = Path(__file__).parent.parent / "suites"
    cases = collect(suites)
    assert cases, "no cases found"
    for case in cases:
        run = execute(CPYTHON, case, timeout_s=60)
        assert run.returncode == 0, f"{case.name} failed under the oracle:\n{run.stderr.decode()}"


class TestReport:
    def test_writing_a_report_produces_valid_json(self, tmp_path):
        """The path CI takes and local runs do not.

        This was a real bug. Summary is a slots dataclass, so reading
        __dict__ raised AttributeError, and it only ran when --out was
        passed, which no local run and no other test did.
        """
        import json

        from kohebi_compat.report import summarise, write

        results = [
            Result(case="a.py", outcome=Outcome.MATCH),
            Result(case="b.py", outcome=Outcome.MISMATCH, disagreed=["stdout"]),
        ]
        write(summarise(results), results, tmp_path)

        data = json.loads((tmp_path / "summary.json").read_text())
        assert data["total"] == 2
        assert data["disagreements"]["stdout"] == 1
        assert "b.py" in (tmp_path / "report.md").read_text()

    def test_oracle_python_overrides_the_command(self, tmp_path):
        """Comparing PyPy against a 3.14 oracle measures the version gap.

        PyPy 7.3.23 implements Python 3.11. Without this override, most of
        what the suite reports is three releases of error message rewording,
        which says nothing about PyPy and would say nothing about kohebi.
        """
        case = tmp_path / "c.py"
        case.write_text("print('ok')")
        rc = main([str(tmp_path), "--against", "cpython", "--oracle-python", sys.executable, "-q"])
        assert rc == 0

    def test_a_missing_oracle_python_is_an_error_not_a_pass(self, tmp_path):
        (tmp_path / "c.py").write_text("print('ok')")
        with pytest.raises(SystemExit) as e:
            main([str(tmp_path), "--oracle-python", "/nonexistent/python-xyz"])
        assert e.value.code != 0

    def test_a_mismatch_says_what_actually_differed(self, tmp_path):
        """A report that only names the interpreter is a report nobody acts on."""
        case = tmp_path / "c.py"
        case.write_text("print('hello')")
        liar = Interpreter("liar", (sys.executable, "-c", "print('goodbye'); raise SystemExit"))
        # The liar ignores the script path appended after its argv and prints
        # something else, which is exactly the shape of a real divergence.
        result = compare(case, oracle=CPYTHON, against=[liar])
        assert result.outcome is Outcome.MISMATCH
        detail = "; ".join(result.detail["liar"])
        assert "stdout" in detail
        assert "hello" in detail
        assert "goodbye" in detail

    def test_a_case_runs_even_though_cwd_is_a_scratch_directory(self, tmp_path):
        """The bug that made every case fail to launch.

        compare() runs each case in a fresh temp directory so a case can write
        files without touching the repo. The script path has to survive that.
        """
        case = tmp_path / "c.py"
        case.write_text("print('ran')")
        result = compare(case, oracle=CPYTHON, against=[])
        assert result.outcome is Outcome.MATCH
        assert result.oracle is not None
        assert result.oracle.stdout == b"ran\n"

    def test_tolerate_mismatch_forgives_a_disagreement(self, tmp_path):
        """PyPy and GraalPy disagree with CPython on purpose.

        Their jobs exist to record how much, so a mismatch there is data.
        Without this the alternatives jobs are red on every run, and a check
        that is always red is a check nobody reads.
        """
        # A case that answers differently the second time it runs, which is
        # how CPython is made to disagree with itself without a stub
        # interpreter that would only work on one platform. The oracle prints
        # 1 and the candidate prints 2.
        (tmp_path / "c.py").write_text(
            "import pathlib\n"
            "p = pathlib.Path('counter')\n"
            "p.write_text(p.read_text() + 'x' if p.exists() else 'x')\n"
            "print(len(p.read_text()))\n"
        )
        argv = [str(tmp_path), "--against", "cpython", "-q", "--tolerate-mismatch"]
        assert main(argv) == 0
        assert main(argv[:-1]) == 1

    def test_tolerate_mismatch_still_fails_when_nothing_ran(self, tmp_path):
        """The distinction the flag has to preserve.

        Forgiving a disagreement is fine. Forgiving a suite that could not run
        is how a broken harness reports success, which this suite has already
        done once.
        """
        (tmp_path / "c.py").write_text("raise SystemExit(1)")
        rc = main([str(tmp_path), "--against", "cpython", "-q", "--tolerate-mismatch"])
        assert rc == 1

    def test_an_oracle_that_cannot_run_the_case_is_not_a_match(self, tmp_path):
        """The guard that would have caught the launch bug on the first run.

        With no correct answer to compare against, the only honest outcome is
        that the oracle failed. Reporting a match here is how a suite goes
        green while running nothing at all.
        """
        case = tmp_path / "c.py"
        case.write_text("this is not python(")
        result = compare(case, oracle=CPYTHON, against=[])
        assert result.outcome is Outcome.ORACLE_FAILED
        assert not result.passed
        assert "exited" in result.note
