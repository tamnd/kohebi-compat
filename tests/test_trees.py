"""Tests for the parser differential.

The same shape as the tokenizer tests next door and for the same reason: a
fake kohebi prints whatever the test needs, so every outcome can be reached
without waiting for a real one to be wrong.

The one thing here that is worth testing on its own is `first_difference`. A
dump of a real module is one line tens of thousands of characters long, and a
report that says "character 41022" is a report nobody acts on, so the part that
turns an offset into the name of a node is the part that makes a mismatch
worth reading.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from kohebi_compat.corpus import Exclusions, Failure, FileOutcome
from kohebi_compat.trees import (
    _enclosing_node,
    compare_file,
    compare_source,
    cpython_tree,
    first_difference,
    oracle_is_usable,
    run,
)


def dump(source: str) -> str:
    """What the oracle prints, so a test can hand the fake the right answer."""
    return ast.dump(ast.parse(source), include_attributes=True)


class TestComparing:
    def test_identical_dumps_match(self, fake_kohebi):
        source = "x = 1\n"
        result = compare_source(source, kohebi=fake_kohebi(out=dump(source) + "\n"))
        assert result.outcome is FileOutcome.MATCH

    def test_a_trailing_newline_is_not_a_difference(self, fake_kohebi):
        source = "pass\n"
        result = compare_source(source, kohebi=fake_kohebi(out=dump(source)))
        assert result.outcome is FileOutcome.MATCH

    def test_a_different_tree_is_a_mismatch_that_names_the_node(self, fake_kohebi):
        source = "x = 1\n"
        wrong = dump(source).replace("value=1", "value=2")
        result = compare_source(source, kohebi=fake_kohebi(out=wrong))
        assert result.outcome is FileOutcome.MISMATCH
        assert "Constant" in result.detail

    def test_a_wrong_position_is_caught(self, fake_kohebi):
        """The half that is easy to get wrong and easy to not notice."""
        source = "x = 1\n"
        wrong = dump(source).replace("col_offset=4", "col_offset=5")
        result = compare_source(source, kohebi=fake_kohebi(out=wrong))
        assert result.outcome is FileOutcome.MISMATCH

    def test_a_gap_we_admit_to_is_not_a_wrong_answer(self, fake_kohebi):
        kohebi = fake_kohebi(err="NotImplementedError: match statements\n", code=1)
        result = compare_source("x = 1\n", kohebi=kohebi)
        assert result.outcome is FileOutcome.UNSUPPORTED
        assert result.passed

    def test_refusing_a_file_cpython_parses_is_a_false_reject(self, fake_kohebi):
        kohebi = fake_kohebi(err="SyntaxError: invalid syntax\n", code=1)
        result = compare_source("x = 1\n", kohebi=kohebi)
        assert result.outcome is FileOutcome.FALSE_REJECT
        assert not result.passed

    def test_parsing_a_file_cpython_refuses_is_a_false_accept(self, fake_kohebi):
        result = compare_source("x = (\n", kohebi=fake_kohebi(out="Module(body=[])"))
        assert result.outcome is FileOutcome.FALSE_ACCEPT
        assert not result.passed

    def test_the_same_refusal_matches(self, fake_kohebi):
        kohebi = fake_kohebi(err="SyntaxError: '(' was never closed\n", code=1)
        result = compare_source("x = (\n", kohebi=kohebi)
        assert result.outcome is FileOutcome.MATCH

    def test_a_different_refusal_is_the_wrong_message(self, fake_kohebi):
        kohebi = fake_kohebi(err="SyntaxError: invalid syntax\n", code=1)
        result = compare_source("x = (\n", kohebi=kohebi)
        assert result.outcome is FileOutcome.WRONG_MESSAGE
        assert "never closed" in result.detail


class TestTheOracle:
    def test_a_file_is_parsed_in_the_encoding_it_declares(self):
        tree = cpython_tree(b"# coding: latin-1\nx = 'caf\xe9'\n")
        assert not isinstance(tree, Failure)
        assert "caf\xe9" in tree

    def test_a_file_that_is_not_utf8_gets_the_compilers_verdict(self):
        verdict = cpython_tree(b'print("b\xf6se")\n')
        assert isinstance(verdict, Failure)
        assert verdict.kind == "SyntaxError"

    def test_a_null_byte_is_reported_rather_than_crashing(self):
        verdict = cpython_tree(b"x = 1\x00\n")
        assert isinstance(verdict, Failure)
        assert verdict.kind == "SyntaxError"


class TestTheOracleVersion:
    """`ast.dump` grew `show_empty` in 3.13 and it defaults to false.

    Before that an optional empty list was printed and after it is left out, so
    an older oracle disagrees with us about every file containing a class or a
    function and none of it is about the tree. Saying so once beats reporting
    it two thousand times.
    """

    def test_the_running_interpreter_is_judged_by_its_own_version(self):
        """The harness tests run on 3.12 as well, so this asserts the rule
        rather than a verdict. Every other test in this file holds `ast.dump`
        up against itself and passes on any version."""
        assert (oracle_is_usable() is None) == (sys.version_info[:2] >= (3, 13))

    def test_313_and_later_are_accepted(self):
        assert oracle_is_usable((3, 13)) is None
        assert oracle_is_usable((3, 14)) is None
        assert oracle_is_usable((4, 0)) is None

    def test_312_is_refused_with_the_reason(self):
        why = oracle_is_usable((3, 12))
        assert why is not None
        assert "3.12" in why
        assert "ast.dump" in why
        assert "Compare tokens instead" in why

    def test_the_command_refuses_rather_than_reporting_thousands_of_bugs(self, monkeypatch):
        from kohebi_compat import trees
        from kohebi_compat.__main__ import main

        monkeypatch.setattr(trees, "oracle_is_usable", lambda: "no good, and here is why")
        with pytest.raises(SystemExit) as refused:
            main(["trees"])
        assert refused.value.code == 2


class TestFirstDifference:
    def test_it_names_the_innermost_open_node(self):
        ours = "Module(body=[Assign(value=Constant(value=1))])"
        theirs = "Module(body=[Assign(value=Constant(value=2))])"
        assert "in Constant at character" in first_difference(ours, theirs)

    def test_it_reads_through_a_paren_inside_a_string(self):
        """A name like `f(x)` in a docstring is text, not a node."""
        ours = "Module(body=[Expr(value=Constant(value='call f(x) here', kind=None))])"
        theirs = ours.replace("kind=None", "kind='u'")
        assert "in Constant at character" in first_difference(ours, theirs)

    def test_a_truncated_dump_is_still_reported(self):
        theirs = "Module(body=[Pass(lineno=1)])"
        message = first_difference("Module(body=[Pass(", theirs)
        assert "Pass" in message

    def test_a_difference_at_the_very_top_has_no_node_to_name(self):
        assert "the tree" in first_difference("Module()", "Interactive()")

    def test_it_shows_both_sides(self):
        message = first_difference("Module(body=[a])", "Module(body=[b])")
        assert "we wrote 'a])'" in message
        assert "CPython wrote 'b])'" in message

    def test_a_window_keeps_the_message_short(self):
        long = "x" * 500
        message = first_difference(f"Module({long}", f"Module({long.upper()}")
        assert len(message) < 300

    def test_nothing_open_means_nothing_named(self):
        assert _enclosing_node("Module(body=[])") is None


class TestOverACorpus:
    def test_an_unreadable_file_is_recorded_rather_than_raised(self, tmp_path, fake_kohebi):
        result = compare_file(tmp_path / "gone.py", kohebi=fake_kohebi())
        assert result.outcome is FileOutcome.UNREADABLE

    def test_an_excluded_file_is_never_handed_to_kohebi(self, tmp_path, fake_kohebi):
        path = tmp_path / "skip_me.py"
        path.write_text("x = (\n")
        rules = Exclusions((("skip_me.py", "a reason"),))
        [result] = run([path], kohebi=fake_kohebi(), exclusions=rules, jobs=1)
        assert result.outcome is FileOutcome.EXCLUDED
        assert result.detail == "a reason"

    def test_every_file_gets_exactly_one_result(self, tmp_path, fake_kohebi):
        paths = []
        for i in range(5):
            path = tmp_path / f"m{i}.py"
            path.write_text("pass\n")
            paths.append(path)
        results = list(run(paths, kohebi=fake_kohebi(out=dump("pass\n")), exclusions=Exclusions()))
        assert [r.path for r in results] == paths
        assert all(r.outcome is FileOutcome.MATCH for r in results)


@pytest.mark.parametrize(
    "source",
    [
        "x = 1\n",
        "def f(a, b=1, *c, d, **e): return a\n",
        "class C:\n    async def m(self):\n        async with a as b: pass\n",
        "match x:\n    case [1, 2, *rest]: pass\n",
        "x = [i async for i in a if i]\n",
        "type Alias[T] = list[T]\n",
        "x: int = 1\n",
        "with (open('a') as f, open('b') as g): pass\n",
        "x = f'{a!r:>{w}}'\n",
        "try:\n    pass\nexcept* ValueError as e:\n    pass\n",
    ],
)
def test_the_oracle_handles_what_the_corpus_will_throw_at_it(source: str):
    """Not a test of kohebi. A test that the oracle side does not fall over.

    If `cpython_tree` raised on any of these, every file using them would be
    reported as a kohebi bug, which is the worst kind of wrong number.
    """
    tree = cpython_tree(source.encode())
    assert not isinstance(tree, Failure), tree
    assert tree.startswith("Module(")


def test_the_default_corpus_is_full_of_real_python():
    """The corpus discovery is shared, so this is a smoke test of the seam."""
    from kohebi_compat.corpus import default_corpus

    root = default_corpus()
    assert root.is_dir()
    assert len(list(root.glob("*.py"))) > 50
    assert (root / "os.py").exists()


def test_paths_come_back_as_paths(tmp_path, fake_kohebi):
    path = tmp_path / "a.py"
    path.write_text("pass\n")
    result = compare_file(path, kohebi=fake_kohebi(out=dump("pass\n")))
    assert isinstance(result.path, Path)
