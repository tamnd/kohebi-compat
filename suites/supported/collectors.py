"""The builtins that walk something and give back a container.

`list`, `tuple`, `set` and `sorted`. The first three are one walk with three
endings, and every one of them takes nothing at all as well, which is the
empty container rather than a refusal. `sorted` is the same walk with a stable
sort on the end of it.

A set is never printed here. kohebi orders a set repr by insertion and CPython
orders it by hash, so `sorted(set(...))` is what a set is checked through,
which works because sorting a set walks it and gives back a list. That is also
the only thing in this file that would have been impossible to write before
`sorted` existed.

Nothing here calls a method on a value or writes a generator expression,
because neither exists yet.
"""

# One walk, four endings, and the same source walked four times.
source = "cab"
print(list(source), tuple(source), sorted(source), sorted(set(source)))
print(list(range(4)), tuple(range(4)), sorted(range(4)))
print(list([1, 2]), tuple((1, 2)), sorted([2, 1]))
print(list({1: "a", 2: "b"}), tuple({1: "a"}), sorted({2: "b", 1: "a"}))

# Nothing at all is the empty one rather than a refusal, and each of the four
# is a different empty thing.
print(list(), tuple(), sorted([]), len(set()))
print(list([]), tuple(()), sorted(""), len(set("")))

# A set drops the duplicates and keeps one of each, which is visible through a
# sort without depending on which order a set walks in.
print(sorted(set([3, 1, 2, 1, 3])), len(set([3, 1, 2, 1, 3])))
print(sorted(set("abracadabra")), len(set("abracadabra")))
print(sorted(set(range(3)) & set(range(1, 5))), sorted(set([1]) | set([2])))

# True and 1 are the same key, so a set keeps whichever arrived first and the
# other one is dropped rather than kept alongside it.
print(len(set([1, True])), len(set([True, 1])), len(set([0, False, 0.0])))


def squares(n):
    """A generator, so that the walk is stepping Python rather than a list."""
    for i in range(n):
        yield i * i


print(list(squares(5)), tuple(squares(3)), sorted(squares(4)))
print(sorted(set(squares(4))), len(set(squares(4))))

# A tuple of a list is a copy rather than the same object, which is what makes
# the first of these two answers what it is.
values = [1, 2]
copy = list(values)
print(copy == values, copy is values, tuple(values) == (1, 2))

# Sorting is stable, so elements that compare equal come out in the order they
# went in, and `reverse=True` reverses the groups without reversing what is
# inside them.
pairs = []
for i in range(9):
    pairs = pairs + [(i % 3, i)]
print(sorted(pairs))
print(sorted(pairs, reverse=True))

# Which is not the same as sorting and then reversing, and the difference is
# exactly the elements that compare equal.


def rank(pair):
    """A key blind to everything that tells the members of a group apart."""
    return pair[0]


print(sorted(pairs, key=rank))
print(sorted(pairs, key=rank, reverse=True))

# A key decides the order and the element is what comes back, so this sorts a
# list of strings by length and a mixed list that could not be sorted at all.
print(sorted(["bb", "a", "ccc"], key=len))
print(sorted([1, "a", 2.5], key=str))
# `key=None` is no key rather than a key of None, and a key is never called on
# a walk with nothing in it, so the second of these is not a refusal.
print(sorted([1, 2], key=None), sorted([], key=1))

# The key is called once per element, in the order the elements arrived, and
# `reverse=True` turns the list round after the keys are taken rather than
# before, which a key with a side effect can see.
asked = [0]


def watched(value):
    """A key that records what it was asked about."""
    asked[0] = asked[0] * 10 + value
    return -value


print(sorted([3, 1, 2], key=watched), asked[0])
asked[0] = 0
print(sorted([3, 1, 2], key=watched, reverse=True), asked[0])

# Long enough that the sort needs more than one merge pass, with an odd run
# left over, which is where an off by one in one would show.
scattered = []
for i in range(11):
    scattered = scattered + [(i * 7) % 11]
print(scattered)
print(sorted(scattered), sorted(scattered, reverse=True))
print(sorted(sorted(scattered)) == sorted(scattered))


def refusal(thunk):
    """The message a call was refused with, as a program would see it."""
    try:
        thunk()
    except TypeError as e:
        return "TypeError: " + str(e)
    return "no refusal"


# The three constructors share a pair of messages and `sorted` has one of its
# own, which says `sort()` because in CPython this is `list.sort` under another
# name and the complaint comes from there.
print(refusal(lambda: list(1, 2)))
print(refusal(lambda: tuple(1, 2)))
print(refusal(lambda: set(1, 2)))
print(refusal(lambda: list(x=1)))
print(refusal(lambda: sorted()))
print(refusal(lambda: sorted([1], [2])))
print(refusal(lambda: sorted(x=1)))
print(refusal(lambda: sorted([1], foo=2)))

# And the ones that are about the argument rather than about the call.
print(refusal(lambda: list(1)))
print(refusal(lambda: set(None)))
print(refusal(lambda: sorted(1)))
print(refusal(lambda: set([[]])))
print(refusal(lambda: sorted([1, "a"])))
print(refusal(lambda: sorted(["a", 1])))
print(refusal(lambda: sorted([1, "a"], reverse=True)))
print(refusal(lambda: sorted([1], key=1)))
