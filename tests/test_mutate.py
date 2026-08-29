"""Tests for the generated corpus.

A generator is harder to test than a fixed corpus, because the thing it
produces is different every time the standard library underneath it changes.
So what is checked here is not which files come out. It is the three promises
the corpus makes to anyone reading a percentage derived from it.

Every file in it is refused by CPython. Otherwise the denominator includes
files that measure nothing, and the number quietly means something else.

The same seed gives the same corpus. Otherwise two runs are not comparable and
a floor in CI is a coin toss.

The file written to disk is the file that was checked. That one sounds like it
cannot fail until you try to put a provenance comment at the top of each
mutant, at which point a module with a coding cookie on its first line gets a
different meaning than the one the generator validated.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from kohebi_compat import mutate

MODULE = '''\
"""A module with enough shape to break in an interesting place."""

import sys


def total(values, start=0):
    running = start
    for value in values:
        if value is None:
            continue
        running = running + value
    return running


class Counter:
    def __init__(self, name):
        self.name = name
        self.seen = {}

    def add(self, key, weight=1):
        self.seen[key] = self.seen.get(key, 0) + weight
        return self

    def report(self):
        return ", ".join(f"{k}={v}" for k, v in sorted(self.seen.items()))


if __name__ == "__main__":
    print(total([1, 2, 3]), file=sys.stderr)
'''


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A standard library of one real looking module."""
    root = tmp_path / "lib"
    root.mkdir()
    (root / "counting.py").write_text(MODULE, encoding="utf-8")
    return root


def test_every_mutant_is_a_file_cpython_refuses(library: Path) -> None:
    made = mutate.generate(library, count=25, seed=1, smallest=1)
    assert made, "the generator produced nothing at all"
    for mutant in made:
        assert mutate.refused(mutant.source, mutant.name), (
            f"{mutant.name} came from {mutant.origin} line {mutant.line} by "
            f"{mutant.edit} and CPython compiles it, so it measures nothing"
        )


def test_the_same_seed_gives_the_same_corpus(library: Path) -> None:
    first = mutate.generate(library, count=15, seed=7, smallest=1)
    second = mutate.generate(library, count=15, seed=7, smallest=1)
    assert [m.source for m in first] == [m.source for m in second]


def test_a_different_seed_gives_a_different_corpus(library: Path) -> None:
    first = mutate.generate(library, count=15, seed=7, smallest=1)
    other = mutate.generate(library, count=15, seed=8, smallest=1)
    assert [m.source for m in first] != [m.source for m in other]


def test_what_is_written_is_what_was_checked(library: Path, tmp_path: Path) -> None:
    # Not a tautology. It fails the moment anything is prepended to a mutant,
    # which is the obvious way to record where it came from.
    made = mutate.generate(library, count=10, seed=3, smallest=1)
    paths = mutate.write(made, tmp_path / "out")
    for path, mutant in zip(paths, made, strict=True):
        assert path.read_text(encoding="utf-8") == mutant.source


def test_where_each_one_came_from_is_written_beside_them(library: Path, tmp_path: Path) -> None:
    made = mutate.generate(library, count=10, seed=3, smallest=1)
    mutate.write(made, tmp_path / "out")
    index = (tmp_path / "out" / "index.txt").read_text(encoding="utf-8").splitlines()
    assert len(index) == len(made)
    for line, mutant in zip(index, made, strict=True):
        assert line.startswith(f"{mutant.name}\t{mutant.origin}\t")


def test_a_file_too_small_to_break_interestingly_is_not_chosen(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "tiny.py").write_text("x = 1\n", encoding="utf-8")
    (root / "counting.py").write_text(MODULE, encoding="utf-8")
    assert mutate.sources(root, smallest=8, largest=400) == [root / "counting.py"]


def test_a_blank_line_or_a_comment_has_nothing_to_break() -> None:
    rng = random.Random(0)
    assert mutate.break_line("\n", rng) is None
    assert mutate.break_line("    # explains the next line\n", rng) is None


def test_a_line_that_does_not_tokenize_on_its_own_is_left_alone() -> None:
    # The first line of a call that runs over several is not a program on its
    # own, and the token edits have nothing to work with. Deleting a token from
    # a half read line would mean deleting text nobody located. The character
    # edits still apply to it, which is why this asks `line_tokens` rather than
    # `break_line`.
    assert mutate.line_tokens("    result = compute(first,\n") is None
    assert mutate.line_tokens("    value,\n") == ["value", ","]


def test_generating_from_a_library_with_nothing_usable_gives_nothing(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert mutate.generate(root, count=5, seed=1) == []
