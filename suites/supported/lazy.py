"""The builtins that give back a walk rather than an answer.

`map` and `filter`. What makes them different from everything else in
`builtins` that takes an iterable is that calling one does nothing: the
function is not called, no element is read, and the function is not even
checked for being callable. All of that waits until something steps the object
that came back, which is what makes `map` over something too big to hold in
memory a program rather than a mistake.

Nothing here calls a method on a value or writes a generator expression,
because neither exists yet, and nothing prints a set, because kohebi orders a
set repr by insertion and CPython orders it by hash.
"""


def double(value):
    """The function most of the maps below apply."""
    return value + value


def odd(value):
    """The predicate most of the filters below ask."""
    return value % 2 == 1


def pair(left, right):
    """Two iterables worth of arguments, so a map can be seen to take one of
    each."""
    return (left, right)


def three(one, two, few):
    """The same for three, which is where the strict wording grows a range."""
    return one


# One walk with a function on the end of it, and the answers collected by
# whatever asked for them.
print(list(map(double, [1, 2, 3])), list(map(abs, [-1, 2])))
print(list(filter(odd, range(6))), list(filter(None, [0, 1, "", "a", [], [0]])))
print(tuple(map(double, (1, 2))), sorted(filter(odd, [3, 1, 2])))
print(sum(map(double, [1, 2])), max(filter(odd, [2, 5, 4, 7])), min(map(abs, [-3, 2])))
print(sorted(set(map(double, [1, 1, 2]))), len(set(map(double, [1, 1, 2]))))
print(any(map(odd, [2, 4])), all(map(odd, [1, 3])), sorted(map(str, range(3))))

# `map` takes one value from each iterable and stops when the shortest one
# does, and the arguments go to the function in the order they were written.
print(list(map(pair, [1, 2, 3], "ab")))
print(list(map(pair, "ab", [1, 2, 3])))
print(list(map(pair, [], [1])), list(map(pair, [1], [])))
print(list(map(three, [1, 2], [3, 4], [5, 6])))

# `filter(None, xs)` is not a predicate that says no to everything, it is no
# predicate at all, and then an element's own truth is the answer.
print(list(filter(None, [0, 1, 2])), list(filter(None, "")), list(filter(None, [0])))

# Both are their own iterator, so `iter(x) is x` and a half consumed one
# carries on rather than starting again.
walk = map(double, [1, 2, 3])
print(iter(walk) is walk, bool(walk))
print(next(walk), list(walk), list(walk))
kept = filter(None, [0, 1, 2])
print(iter(kept) is kept, next(kept), list(kept))
for value in map(double, [1, 2]):
    print(value)
for value in filter(odd, range(5)):
    print(value)


def counted(n, upto):
    """A generator that says how far it was walked."""
    for i in range(n):
        upto[0] = i + 1
        yield i


# A generator is as good an argument as a list, on either side.
pulled = [0]
print(list(map(double, counted(3, pulled))), pulled[0])
pulled[0] = 0
print(list(filter(odd, counted(4, pulled))), pulled[0])

# Nothing happens until something asks. Two objects are built here and the
# function is not called once, and neither of the two is checked for being
# callable either.
asked = [0]


def watched(value):
    """A function that records that it was called."""
    asked[0] = asked[0] + 1
    return value


mapped = map(watched, [1, 2, 3])
sifted = filter(watched, [1, 2, 3])
print(asked[0], next(mapped), asked[0], next(sifted), asked[0])
print(map(1, [1]) is not None, filter(1, [1]) is not None)

# A `map` past its end keeps pulling on the iterables that were longer, which
# looks like a bug and is what CPython does.
left = [0]
right = [0]
uneven = map(pair, counted(5, left), counted(2, right))
print(list(uneven), left[0], right[0])
print(next(uneven, "gone"), left[0], right[0])
print(next(uneven, "gone"), left[0], right[0])


def caught(thunk):
    """What a call was refused with, as a program would see it."""
    try:
        return thunk()
    except TypeError as e:
        return "TypeError: " + str(e)
    except ValueError as e:
        return "ValueError: " + str(e)


# `strict=True` is for a caller who meant the lengths to match. The wording
# names the odd argument out and the ones that agreed with each other, and the
# ones that agreed are a range when there is more than one of them.
print(caught(lambda: list(map(abs, [-1, 2], strict=True))))
print(caught(lambda: list(map(pair, [1, 2], [3, 4], strict=True))))
print(caught(lambda: list(map(pair, [1, 2], [3], strict=True))))
print(caught(lambda: list(map(pair, [1], [3, 4], strict=True))))
print(caught(lambda: list(map(pair, [], [1], strict=True))))
print(caught(lambda: list(map(pair, [1], [], strict=True))))
print(caught(lambda: list(map(pair, [], [], strict=True))))
print(caught(lambda: list(map(three, [1], [2], [3, 4], strict=True))))
print(caught(lambda: list(map(three, [1], [2, 2], [3, 4], strict=True))))
print(caught(lambda: list(map(three, [1, 1], [2, 2], [3], strict=True))))
print(caught(lambda: list(map(three, [1, 1], [2], [3], strict=True))))
print(caught(lambda: list(map(pair, [1, 2], [3], strict=False))))
print(caught(lambda: list(map(pair, [1, 2], [3], strict=1))))

# And it stops at the first walk that still had something, so a later one is
# left where it was.
one = [0]
two = [0]
few = [0]
walks = [counted(1, one), counted(3, two), counted(3, few)]
print(caught(lambda: list(map(three, walks[0], walks[1], walks[2], strict=True))))
print(one[0], two[0], few[0])

# What a walk cannot do is the call's complaint and what a call cannot do is
# the step's, which is the whole of what being lazy decides.
print(caught(lambda: map()))
print(caught(lambda: map(abs)))
print(caught(lambda: map(foo=1)))
print(caught(lambda: map(abs, foo=1)))
print(caught(lambda: map(strict=True)))
print(caught(lambda: map(abs, 1)))
print(caught(lambda: map(abs, [1], True)))
print(caught(lambda: list(map(1, [1]))))
print(caught(lambda: list(map(abs, [-1], [2]))))
print(caught(lambda: filter()))
print(caught(lambda: filter(abs)))
print(caught(lambda: filter(abs, [1], [2])))
print(caught(lambda: filter(x=1)))
print(caught(lambda: filter(abs, [1], x=1)))
print(caught(lambda: filter(abs, 1)))
print(caught(lambda: list(filter(1, [1]))))
print(caught(lambda: len(map(abs, [1]))))
print(caught(lambda: list(map(abs, [1, "a"]))))
print(caught(lambda: list(filter(abs, [1, "a"]))))
