"""Tests for the tokenizer differential.

Most of these do not need kohebi at all. They stand in a fake binary that
prints a token stream we control, which is how the interesting cases get
tested: a real kohebi that agrees with CPython cannot demonstrate what happens
when it does not.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from kohebi_compat.tokens import (
    Exclusions,
    Failure,
    TokenOutcome,
    _failure_from_report,
    _first_difference,
    compare_source,
    compiler_verdict,
    cpython_tokens,
    default_corpus,
)

# A stand-in for the kohebi binary. It reads Python source on stdin and prints
# whatever the test told it to print, so the harness can be driven into every
# outcome without a real runtime.
_FAKE = """\
import sys
sys.stdin.read()
out = {out!r}
err = {err!r}
sys.stdout.write(out)
sys.stderr.write(err)
sys.exit({code})
"""


@pytest.fixture
def fake_kohebi(tmp_path: Path):
    def make(*, out: str = "", err: str = "", code: int = 0) -> list[str]:
        script = tmp_path / f"fake_{abs(hash((out, err, code)))}.py"
        script.write_text(_FAKE.format(out=out, err=err, code=code))
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return [sys.executable, str(script)]

    return make


def _jsonl(*tokens: tuple[str, int, int, int, int, str]) -> str:
    import json

    return "".join(
        json.dumps({"type": t, "start": [a, b], "end": [c, d], "text": s}) + "\n"
        for t, a, b, c, d, s in tokens
    )


def test_identical_streams_match(fake_kohebi):
    source = "x\n"
    theirs = cpython_tokens(source)
    assert not isinstance(theirs, Failure)
    out = _jsonl(*[(t[0], t[1][0], t[1][1], t[2][0], t[2][1], t[3]) for t in theirs])
    result = compare_source(source, kohebi=fake_kohebi(out=out))
    assert result.outcome is TokenOutcome.MATCH


def test_a_wrong_column_is_a_mismatch(fake_kohebi):
    out = _jsonl(
        ("NAME", 1, 0, 1, 1, "x"),
        ("NEWLINE", 1, 1, 1, 2, "\n"),
        ("ENDMARKER", 9, 9, 9, 9, ""),
    )
    result = compare_source("x\n", kohebi=fake_kohebi(out=out))
    assert result.outcome is TokenOutcome.MISMATCH
    assert "token 2" in result.detail


def test_a_short_stream_says_where_it_stopped(fake_kohebi):
    out = _jsonl(("NAME", 1, 0, 1, 1, "x"))
    result = compare_source("x\n", kohebi=fake_kohebi(out=out))
    assert result.outcome is TokenOutcome.MISMATCH
    assert "we stopped after 1 tokens" in result.detail


def test_an_admitted_gap_is_not_a_wrong_answer(fake_kohebi):
    kohebi = fake_kohebi(
        err='  File "<stdin>", line 1\nNotImplementedError: f-strings are not implemented yet\n',
        code=1,
    )
    result = compare_source('f"{x}"\n', kohebi=kohebi)
    assert result.outcome is TokenOutcome.UNSUPPORTED
    assert result.passed


def test_refusing_a_file_cpython_accepts_is_a_false_reject(fake_kohebi):
    kohebi = fake_kohebi(err="SyntaxError: invalid syntax\n", code=1)
    result = compare_source("x = 1\n", kohebi=kohebi)
    assert result.outcome is TokenOutcome.FALSE_REJECT
    assert not result.passed


def test_accepting_a_file_cpython_refuses_is_a_false_accept(fake_kohebi):
    out = _jsonl(("NAME", 1, 0, 1, 1, "x"))
    result = compare_source('x = "abc\n', kohebi=fake_kohebi(out=out))
    assert result.outcome is TokenOutcome.FALSE_ACCEPT


def test_the_same_refusal_in_different_words_is_a_wrong_message(fake_kohebi):
    kohebi = fake_kohebi(err="SyntaxError: string was not closed\n", code=1)
    result = compare_source('x = "abc\n', kohebi=kohebi)
    assert result.outcome is TokenOutcome.WRONG_MESSAGE
    assert "unterminated string literal" in result.detail


def test_the_same_refusal_in_the_same_words_matches(fake_kohebi):
    kohebi = fake_kohebi(
        err="SyntaxError: unterminated string literal (detected at line 1)\n", code=1
    )
    result = compare_source('x = "abc\n', kohebi=kohebi)
    assert result.outcome is TokenOutcome.MATCH


def test_the_compiler_outranks_the_tokenize_module(fake_kohebi):
    # `tokenize` returns a NAME for this. The compiler refuses it, and the
    # compiler is what a user sees, so refusing it is the right answer.
    source = "€ = 2\n"
    assert not isinstance(cpython_tokens(source), Failure)
    kohebi = fake_kohebi(err="SyntaxError: invalid character '€' (U+20AC)\n", code=1)
    assert compare_source(source, kohebi=kohebi).outcome is TokenOutcome.MATCH


class TestFailureParsing:
    def test_the_last_line_of_the_report_carries_the_message(self):
        report = (
            "  File \"t.py\", line 1\n    x = (\n        ^\nSyntaxError: '(' was never closed\n"
        )
        assert _failure_from_report(report) == Failure("SyntaxError", "'(' was never closed")

    def test_an_indentation_error_keeps_its_own_class(self):
        assert _failure_from_report("IndentationError: unexpected indent\n").kind == (
            "IndentationError"
        )

    def test_an_empty_report_does_not_crash(self):
        assert _failure_from_report("").message == ""


class TestCompilerVerdict:
    def test_valid_source_has_no_verdict(self):
        assert compiler_verdict("x = 1\n") is None

    def test_the_message_carries_no_file_or_line(self):
        verdict = compiler_verdict("x = (\n")
        assert verdict == Failure("SyntaxError", "'(' was never closed")

    def test_a_parenthesis_in_the_message_survives(self):
        # str(exc) would be truncated at the wrong parenthesis here.
        verdict = compiler_verdict("€ = 2\n")
        assert verdict == Failure("SyntaxError", "invalid character '€' (U+20AC)")

    def test_a_null_byte_is_rejected_before_parsing(self):
        verdict = compiler_verdict("x = 1\0\n")
        assert verdict is not None
        assert "null byte" in verdict.message


class TestExclusions:
    def test_a_rule_needs_a_reason(self, tmp_path: Path):
        path = tmp_path / "exclusions.txt"
        path.write_text("*/broken.py\n")
        with pytest.raises(ValueError, match="no reason"):
            Exclusions.load(path)

    def test_an_empty_reason_is_still_no_reason(self, tmp_path: Path):
        path = tmp_path / "exclusions.txt"
        path.write_text("*/broken.py:   \n")
        with pytest.raises(ValueError, match="no reason"):
            Exclusions.load(path)

    def test_comments_and_blank_lines_are_skipped(self, tmp_path: Path):
        path = tmp_path / "exclusions.txt"
        path.write_text("# a note\n\n*/broken.py: it is broken\n")
        assert Exclusions.load(path).rules == [("*/broken.py", "it is broken")]

    def test_a_matching_path_gets_its_reason_back(self):
        rules = Exclusions([("*/tokenizedata/*", "deliberately malformed test data")])
        assert rules.reason_for(Path("a/tokenizedata/b.py")) == ("deliberately malformed test data")
        assert rules.reason_for(Path("a/b.py")) is None

    def test_a_bare_name_matches_the_file_name(self):
        rules = Exclusions([("badsyntax_*.py", "not valid Python on purpose")])
        assert rules.reason_for(Path("/deep/path/badsyntax_3131.py")) is not None

    def test_a_missing_file_excludes_nothing(self, tmp_path: Path):
        assert Exclusions.load(tmp_path / "nope.txt").rules == []


class TestFirstDifference:
    def test_equal_streams_have_none(self):
        stream = [("NAME", (1, 0), (1, 1), "x")]
        assert _first_difference(stream, stream) is None

    def test_an_extra_token_on_our_side_is_named(self):
        theirs = [("NAME", (1, 0), (1, 1), "x")]
        ours = [*theirs, ("ENDMARKER", (2, 0), (2, 0), "")]
        detail = _first_difference(ours, theirs)
        assert detail is not None
        assert "after CPython finished" in detail


class TestDefaultCorpus:
    def test_it_is_the_standard_library_of_this_interpreter(self):
        corpus = default_corpus()
        assert corpus.is_dir()
        assert (corpus / "os.py").exists()

    def test_another_interpreter_is_asked_rather_than_guessed(self):
        assert default_corpus(sys.executable) == default_corpus()


class TestLocalCorpus:
    """The hand written corpus has to stay valid Python.

    A file in it that CPython itself will not tokenize compares one broken
    thing against another and proves nothing, so the ones meant to be valid are
    checked here rather than discovered later.
    """

    @staticmethod
    def _files() -> list[Path]:
        root = Path(__file__).resolve().parent.parent / "corpus" / "local"
        return sorted(root.glob("*.py"))

    def test_the_corpus_is_not_empty(self):
        assert len(self._files()) > 10

    @pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
    def test_cpython_has_an_opinion_about_every_file(self, path: Path):
        source = path.read_text(encoding="utf-8-sig")
        tokens = cpython_tokens(source)
        if isinstance(tokens, Failure):
            # The deliberately broken ones. Each still has to produce a real
            # message, since that message is what the comparison is about.
            assert tokens.message
            assert tokens.kind in ("SyntaxError", "IndentationError", "TabError")
        else:
            assert tokens[-1][0] == "ENDMARKER"


def test_the_repository_exclusions_file_parses():
    root = Path(__file__).resolve().parent.parent
    Exclusions.load(root / "corpus" / "exclusions.txt")


@pytest.mark.skipif(os.name == "nt", reason="the fake binary is a POSIX shebang-free script")
def test_a_file_that_is_not_utf8_is_reported_rather_than_crashing(tmp_path: Path, fake_kohebi):
    from kohebi_compat.tokens import compare_file

    path = tmp_path / "latin1.py"
    path.write_bytes(b"x = '\xff'\n")
    result = compare_file(path, kohebi=fake_kohebi())
    assert result.outcome is TokenOutcome.UNREADABLE
    assert result.passed
