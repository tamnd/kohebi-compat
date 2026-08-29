"""Tests for the refusal differential.

Two halves. The plumbing is tested the way the other two differentials are,
with a fake kohebi that prints whatever the test needs, because a real one that
already agrees with CPython cannot demonstrate a disagreement.

The other half is a test of the corpus itself, which the other differentials do
not need and this one does. `corpus/broken` only measures anything as long as
every file in it is a file CPython refuses. A case that quietly becomes valid,
because a future release accepts it or because somebody fixed a typo in it,
would go on passing forever while checking nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from kohebi_compat.corpus import Exclusions, FileOutcome
from kohebi_compat.errors import (
    compare_file,
    cpython_report,
    first_difference,
    kohebi_report,
    run,
)

BROKEN = Path("corpus/broken")

CASES = sorted(BROKEN.glob("*.py"))


@pytest.fixture
def broken(tmp_path: Path):
    """A file CPython refuses, and the block it prints for it."""

    def make(source: bytes = b"x = '\\u12'\n", name: str = "case.py") -> tuple[Path, str]:
        path = tmp_path / name
        path.write_bytes(source)
        block = cpython_report(path, source)
        assert block is not None, "the fixture has to be a file CPython refuses"
        return path, block

    return make


class TestComparing:
    def test_the_same_block_is_a_match(self, broken, fake_kohebi):
        path, block = broken()
        result = compare_file(path, kohebi=fake_kohebi(err=block, code=1))
        assert result.outcome is FileOutcome.MATCH

    def test_a_trailing_newline_is_not_a_difference(self, broken, fake_kohebi):
        path, block = broken()
        result = compare_file(path, kohebi=fake_kohebi(err=block + "\n", code=1))
        assert result.outcome is FileOutcome.MATCH

    def test_the_right_message_in_the_wrong_place_is_still_wrong(self, broken, fake_kohebi):
        """The whole point of comparing the block rather than the last line."""
        path, block = broken()
        moved = block.replace("line 1", "line 2")
        result = compare_file(path, kohebi=fake_kohebi(err=moved, code=1))
        assert result.outcome is FileOutcome.WRONG_MESSAGE
        assert "line 2" in result.detail

    def test_carets_of_the_wrong_width_are_a_difference(self, broken, fake_kohebi):
        path, block = broken()
        lines = block.splitlines()
        lines[2] = lines[2] + "^"
        result = compare_file(path, kohebi=fake_kohebi(err="\n".join(lines), code=1))
        assert result.outcome is FileOutcome.WRONG_MESSAGE

    def test_the_wrong_class_is_a_difference(self, broken, fake_kohebi):
        path, block = broken()
        wrong = block.replace("SyntaxError:", "ValueError:")
        result = compare_file(path, kohebi=fake_kohebi(err=wrong, code=1))
        assert result.outcome is FileOutcome.WRONG_MESSAGE

    def test_reading_a_file_cpython_refuses_is_a_false_accept(self, broken, fake_kohebi):
        path, _ = broken()
        result = compare_file(path, kohebi=fake_kohebi(out="Module(body=[])"))
        assert result.outcome is FileOutcome.FALSE_ACCEPT
        assert not result.passed

    def test_a_gap_we_admit_to_is_not_a_wrong_answer(self, broken, fake_kohebi):
        path, _ = broken()
        kohebi = fake_kohebi(err="NotImplementedError: the shift-jis codec\n", code=1)
        result = compare_file(path, kohebi=kohebi)
        assert result.outcome is FileOutcome.UNSUPPORTED
        assert result.passed

    def test_a_file_cpython_reads_does_not_belong_in_the_corpus(self, tmp_path, fake_kohebi):
        path = tmp_path / "fine.py"
        path.write_text("x = 1\n")
        result = compare_file(path, kohebi=fake_kohebi(out="Module(body=[])"))
        assert result.outcome is FileOutcome.MISMATCH
        assert "does not belong" in result.detail

    def test_refusing_a_file_cpython_reads_is_a_false_reject(self, tmp_path, fake_kohebi):
        path = tmp_path / "fine.py"
        path.write_text("x = 1\n")
        kohebi = fake_kohebi(err="SyntaxError: invalid syntax\n", code=1)
        result = compare_file(path, kohebi=kohebi)
        assert result.outcome is FileOutcome.FALSE_REJECT
        assert not result.passed


class TestTheOracle:
    def test_a_bad_escape_gets_the_whole_block(self, broken):
        path, block = broken()
        assert block.startswith(f'  File "{path}", line 1')
        assert "^" in block
        assert block.endswith("truncated \\uXXXX escape")

    def test_the_filename_is_the_path_as_written(self, broken):
        path, block = broken(name="deep.py")
        assert str(path) in block

    def test_a_refusal_with_nothing_attached_is_one_line(self, tmp_path):
        """A null byte is refused before the compiler is told the filename.

        Which class it is has moved between releases, so this asserts the shape
        rather than the name: no `File` line, no source, no carets.
        """
        path = tmp_path / "nul.py"
        path.write_bytes(b"x = 1\x00\n")
        block = cpython_report(path, path.read_bytes())
        assert block is not None
        assert block.endswith("source code string cannot contain null bytes")
        assert "File" not in block

    def test_a_file_cpython_reads_gets_nothing(self, tmp_path):
        path = tmp_path / "fine.py"
        path.write_bytes(b"x = 1\n")
        assert cpython_report(path, path.read_bytes()) is None


class TestFirstDifference:
    def test_it_numbers_the_line_and_shows_both(self):
        message = first_difference("a\nb", "a\nc")
        assert "line 2" in message
        assert "we wrote 'b'" in message
        assert "CPython wrote 'c'" in message

    def test_it_shows_carets_that_a_bare_diff_would_hide(self):
        message = first_difference("    ^^", "    ^")
        assert "'    ^^'" in message
        assert "'    ^'" in message

    def test_a_block_of_the_wrong_length_is_reported_by_length(self):
        message = first_difference("a\nb", "a")
        assert "2 line(s)" in message
        assert "1" in message


class TestOverACorpus:
    def test_an_unreadable_file_is_recorded_rather_than_raised(self, tmp_path, fake_kohebi):
        result = compare_file(tmp_path / "gone.py", kohebi=fake_kohebi())
        assert result.outcome is FileOutcome.UNREADABLE

    def test_an_excluded_file_is_never_handed_to_kohebi(self, broken, fake_kohebi):
        path, _ = broken(name="skip_me.py")
        rules = Exclusions((("skip_me.py", "a reason"),))
        [result] = run([path], kohebi=fake_kohebi(), exclusions=rules, jobs=1)
        assert result.outcome is FileOutcome.EXCLUDED
        assert result.detail == "a reason"

    def test_every_file_gets_exactly_one_result(self, broken, fake_kohebi):
        paths = [broken(name=f"m{i}.py")[0] for i in range(5)]
        results = list(run(paths, kohebi=fake_kohebi(), exclusions=Exclusions(), jobs=2))
        assert [r.path for r in results] == paths


class TestTheBrokenCorpus:
    """The corpus is the test here, so the corpus gets tested."""

    def test_it_is_where_the_command_looks_for_it(self):
        """These tests read a directory and the command defaults to one, and a
        test of a corpus nobody compares is a test of nothing."""
        from kohebi_compat.__main__ import BROKEN as DEFAULT

        assert DEFAULT == BROKEN
        assert BROKEN.is_dir()

    def test_there_are_enough_files_to_mean_something(self):
        assert len(CASES) > 30

    @pytest.mark.parametrize("path", CASES, ids=lambda p: p.name)
    def test_cpython_refuses_it(self, path: Path):
        assert cpython_report(path, path.read_bytes()) is not None

    def test_every_file_is_small_enough_to_read_in_a_failure(self):
        """A case is one refusal. A hundred line file with a bad escape in it
        tests the same thing and reads worse when it is the one that failed."""
        too_big = [p for p in CASES if len(p.read_bytes()) > 200]
        assert not too_big


def test_a_bad_command_line_is_not_a_compatibility_difference(tmp_path):
    """Being told the flag does not exist is not a disagreement about the file.

    Reading it as one turns a one word mistake in the command line into a
    thousand failures with the real reason buried among them, which is exactly
    what happened the first time `--compile` was passed to a kohebi that did
    not have it yet.
    """
    good = tmp_path / "fine.py"
    good.write_text("x = 1\n")
    with pytest.raises(RuntimeError, match="rejected the command line"):
        kohebi_report(good, kohebi=[sys.executable, "-c", "raise SystemExit(2)"])
