"""The builtins, and the places where getting one of them slightly wrong shows.

Most of these have a right answer that is obvious and a second right answer
underneath it that is not. `abs(True)` is an int rather than a bool. `str` and
`repr` differ on a string and agree on a string inside a list. `bool()` with
nothing at all is False rather than an error. `len(range(...))` is refused for
a range no machine word can count even though the range itself walks fine.

Nothing here calls a method on a value or asks for a type object, because
neither exists yet, and nothing prints a set, because kohebi orders a set repr
by insertion and CPython orders it by hash.
"""

# The three that ask one question about one value, and the two ways a number
# can lose its sign.
print(abs(-3), abs(3), abs(-1.5), abs(-0.0))
print(abs(True), abs(False), abs(-(2**70)))

# A bool is an int, so this is 1 and not True, and it prints as 1.
total = abs(True) + abs(True)
print(total, total == 2)

# `str` and `repr` differ on a string and on nothing else, because a container
# prints its elements with `repr` however it was asked to print itself.
print(str("a"), repr("a"))
print(str(["a"]), repr(["a"]))
print(str(1), repr(1), str(1.5), repr(1.5), str(None), repr(None))
print(str(b"ab"), repr(b"ab"))
print(str(()), repr((1,)), str([]), repr({}))

# Neither of them is the empty string by accident: one has no argument and the
# other has an argument that is empty.
print(repr(str()), repr(str("")))

# `str` takes its argument by name too, which almost nothing else here does.
print(str(object=1), str(object="a"))

# Everything has a truth and none of them can refuse to answer.
print(bool(), bool(0), bool(1), bool(-1), bool(0.0))
print(bool(""), bool("a"), bool("0"), bool([]), bool([0]), bool(()), bool({}))
print(bool(None), bool(range(0)), bool(range(1)))

# The truth of a value and the value itself are different things, which is
# what `or` gives back and `bool` does not.
print("" or "fallback", bool("") or "fallback")


def describe(value):
    """What one value is, said three ways.

    The three builtins compose into one line about a value, which is most of
    what they are for. `size` is a separate function only because `len` is the
    one of the four that refuses some of these.
    """
    return repr(value) + " is " + str(bool(value)) + " with len " + str(size(value))


def size(value):
    """`len`, for the things that have one, and -1 for the things that do not."""
    try:
        return len(value)
    except TypeError:
        return -1


for value in ["", "abc", [1, 2], (), {}, {1: 2}, 0, 5, None, 1.5]:
    print(describe(value))

# `len` and the walk it counts agree, and the one length that is a real number
# and still refused is refused for a reason a program can see.
print(len("aé日"), len(b"abcd"), len([1]), len((1, 2)), len({1: 2}))
print(len(range(10)), len(range(2**70, 2**70 + 3)))
try:
    len(range(2**70))
except OverflowError as e:
    print("OverflowError:", e)

# `iter` and `next` are the loop taken apart, and `next` is the only place a
# program can see the end of one.
walk = iter([1, 2])
print(next(walk), next(walk), next(walk, "done"))
try:
    next(walk)
except StopIteration:
    print("stopped")


def counted(n):
    """A generator, so that `next` is stepping Python rather than a container."""
    for i in range(n):
        yield i * i
    return "finished"


g = counted(3)
print(next(g), next(g), next(g))
try:
    next(g)
except StopIteration as e:
    # What the generator returned, which rides on the exception that ends it
    # and is there exactly once.
    print("returned", str(e))
print(next(g, "and afterwards nothing"))


def refusal(thunk):
    """The message a call was refused with, as a program would see it.

    Printed rather than raised, because the words are the thing being checked
    and a traceback would put a line number in front of them.
    """
    try:
        thunk()
    except TypeError as e:
        return str(e)
    return "no refusal"


# CPython is not uniform about any of this and the differences are the point.
# `abs` and `len` count their arguments one way and `bool` another, and only
# one of the two messages has parentheses after the name.
print(refusal(lambda: abs()))
print(refusal(lambda: repr()))
print(refusal(lambda: len([], [])))
print(refusal(lambda: bool(1, 2)))
print(refusal(lambda: bool(x=1)))
print(refusal(lambda: abs(x=1)))

# `str` has the most argument shapes of the four and the most ways to be given
# the wrong one. The encoding is checked before the object is, which is why the
# first of these names the 2 and the second names the 1.
print(refusal(lambda: str(1, 2)))
print(refusal(lambda: str(1, "utf-8")))
print(refusal(lambda: str("a", "utf-8")))
print(refusal(lambda: str(1, object=2)))
print(refusal(lambda: str(1, 2, 3, 4)))
print(refusal(lambda: str(x=1)))

# And the two that are about the value rather than about the call.
print(refusal(lambda: abs("a")))
print(refusal(lambda: len(1)))
