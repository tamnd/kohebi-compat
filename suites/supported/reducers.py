"""The builtins that walk something and give back one value.

`any`, `all`, `sum`, `min` and `max`. What they have in common is that they
step an iterator rather than looking inside a container, so a generator is as
good an argument as a list, and that they stop as early as they are allowed
to, which a generator with a counter in it can see.

Where they differ is in how they count their arguments, and CPython is not
uniform about it. `sum` has three distinct messages for one signature. `min`
and `max` read one argument as a container and two or more as the candidates
themselves. `any` and `all` take exactly one and say so in a fourth way again.

Nothing here calls a method on a value or writes a generator expression,
because neither exists yet, and nothing prints a set, because kohebi orders a
set repr by insertion and CPython orders it by hash.
"""

# Every value has a truth, so neither of these can refuse an element.
print(any([]), any([0, 1]), any([0, 0]), any({}), any(""), any("a"))
print(all([]), all([1, 0]), all([1, 2]), all(""), all([[1], 1]), all([[], 1]))

# The two are each other upside down, which is worth saying out loud because
# it is the definition rather than a coincidence: `all(xs)` is `not any` of
# the elements being false.
values = [[], [0], [1], [0, 1], [1, 1], [0, 0]]
for value in values:
    print(value, any(value), all(value), any(value) == (not all([not x for x in value])))


def counted(n, upto):
    """A generator that says how far it was walked.

    The count goes through a list rather than a name, so that writing to it
    does not make it a local of this function.
    """
    for i in range(n):
        upto[0] = i + 1
        yield i % 2


# `any` stops at the first true element and `all` at the first false one, and
# both walk the whole thing when there is nothing to stop at.
pulled = [0]
print(any(counted(10, pulled)), pulled[0])
pulled[0] = 0
print(all(counted(10, pulled)), pulled[0])
pulled[0] = 0
print(any([0, 0, 0]), all([1, 1, 1]), pulled[0])

# `sum` starts at zero unless told otherwise, and the start is added on the
# left, which is why a list start gives a list and a tuple start a tuple.
print(sum([]), sum([1, 2]), sum([1, 2], 10), sum([1.5, 2]), sum([1.0, 2]))
print(sum([True, True]), sum([[1], [2]], []), sum([(1,)], ()), sum([1], start=10))
print(sum(range(101)), sum(range(0)))

# One walk, three answers, and the same walk done four times gives the same
# four answers because a range can be walked again.
numbers = range(5, 0, -1)
print(sum(numbers), min(numbers), max(numbers), len(numbers))

# One positional argument is a container to walk. Two or more are the
# candidates themselves, which is the only reason this is not 1.
print(min([2, 1], [3]), min(3, 1, 2), max(3, 1, 2))
print(min("cab"), max("cab"), max({1: "a", 2: "b"}))

# A tie keeps the one that came first, and the two can be equal without being
# the same object, so this is visible rather than a detail.
print(min([1], [1]), max([1], [2]), min([0.0, -0.0]), max([1, 1.0]))

# A default only means anything for a walk that turned out to be empty.
print(min([], default=9), max([], default=9), min([1, 2], default=9))


def size(value):
    """`len`, which is what these two are sorted by below."""
    return len(value)


def negated(value):
    """The key that turns `min` into `max` and back."""
    return -value


# A key decides the order and the element is what comes back, which is the
# whole point of having one.
print(min(["aa", "b", "ccc"], key=size), max(["aa", "b", "ccc"], key=size))
print(min("aa", "b", key=size), max(1, 2, 3, key=negated))
print(min([1, 2, 3], key=negated), max([1, 2, 3], key=negated))

# `key=None` is no key rather than a key of None, and a key is never called on
# a walk that has nothing in it.
print(min([1, 2], key=None), max([1, 2], key=None), min([], key=size, default=9))

# The key is called once per element, in the order the elements arrived, and
# not a second time on whatever is currently winning.
asked = [0]


def watched(value):
    """A key that records what it was asked about."""
    asked[0] = asked[0] * 10 + value
    return -value


print(min([3, 1, 2], key=watched), asked[0])
asked[0] = 0
print(max([3, 1, 2], key=watched), asked[0])


def refusal(thunk):
    """The message a call was refused with, as a program would see it."""
    try:
        thunk()
    except TypeError as e:
        return "TypeError: " + str(e)
    except ValueError as e:
        return "ValueError: " + str(e)
    return "no refusal"


# `any` and `all` count their arguments one way.
print(refusal(lambda: any()))
print(refusal(lambda: any(1, 2)))
print(refusal(lambda: any(x=1)))
print(refusal(lambda: all()))
print(refusal(lambda: any(1)))
print(refusal(lambda: all(None)))

# `sum` counts them three ways: the keywords count towards the upper limit and
# not towards the lower one, and the upper complaint is worded differently
# when there is nothing positional to count.
print(refusal(lambda: sum()))
print(refusal(lambda: sum(start=1)))
print(refusal(lambda: sum(a=1, b=2, c=3)))
print(refusal(lambda: sum([1], 2, start=3)))
print(refusal(lambda: sum([1], 1, 2, 3)))
print(refusal(lambda: sum([1], foo=2)))

# And it refuses the two starts that would have worked, because doing it the
# slow way is a mistake worth naming rather than serving.
print(refusal(lambda: sum(["a", "b"], "")))
print(refusal(lambda: sum([], "")))
print(refusal(lambda: sum([b"a"], b"")))
print(refusal(lambda: sum([1, "a"])))
print(refusal(lambda: sum([1], start=None)))

# `min` and `max` count them in a fourth way again, and the empty walk with no
# default is the one refusal here that is not a TypeError.
print(refusal(lambda: min()))
print(refusal(lambda: max()))
print(refusal(lambda: min(key=None)))
print(refusal(lambda: min([])))
print(refusal(lambda: max([])))
print(refusal(lambda: min("")))
print(refusal(lambda: min(1)))
print(refusal(lambda: min([1, "a"])))
print(refusal(lambda: min(3, 1, default=9)))
print(refusal(lambda: min([1], 2, foo=3)))
print(refusal(lambda: min([1], key=1)))
