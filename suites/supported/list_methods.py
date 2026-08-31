"""The methods a list has.

Every one of them, and the ways each one can be called wrongly, because the
wording is where a runtime that reimplements a builtin type goes wrong first
and a program can read all of it.

Nothing here writes a generator expression or formats with `%`, because
neither exists yet, and nothing prints a set, because kohebi orders a set repr
by insertion and CPython orders it by hash.
"""


def caught(thunk):
    """What a call was refused with, as a program would see it."""
    try:
        return thunk()
    except TypeError as e:
        return "TypeError: " + str(e)
    except ValueError as e:
        return "ValueError: " + str(e)
    except IndexError as e:
        return "IndexError: " + str(e)
    except OverflowError as e:
        return "OverflowError: " + str(e)
    except AttributeError as e:
        return "AttributeError: " + str(e)


def show(items, thunk):
    """What a method gave back and what it left behind, which for most of
    these is the interesting half."""
    return (thunk(), items)


# A method is a value looked up on the list, and looking it up twice gives two
# objects rather than one, so neither `is` nor `==` holds between them.
xs = [1, 2]
print(xs.append is xs.append, xs.append == xs.append)
found = xs.append
print(found is found, found == found, bool(found))

# `append` takes exactly one argument and adds it whole, so a list argument
# goes in as one element rather than being spread out.
xs = []
print(show(xs, lambda: xs.append(1)), show(xs, lambda: xs.append([2, 3])))
xs = [1]
xs.append(xs)
print(len(xs), xs[1] is xs)

# `extend` spreads its argument out, and takes anything that can be walked.
xs = [1]
print(show(xs, lambda: xs.extend([2, 3])), show(xs, lambda: xs.extend((4,))))
xs = []
print(show(xs, lambda: xs.extend("abc")), show(xs, lambda: xs.extend(range(2))))
xs = []
print(show(xs, lambda: xs.extend([])), show(xs, lambda: xs.extend(map(abs, [-1]))))

# A list or a tuple argument is taken by its length first, which is what makes
# extending a list with itself twice as long rather than endless.
xs = [1, 2]
xs.extend(xs)
print(xs)


def counted(n, into):
    """A generator that appends to the list being extended as it goes."""
    for i in range(n):
        into.append(99)
        yield i


# A generator is not taken up front, so what it appends is seen.
xs = [1]
xs.extend(counted(2, xs))
print(xs)

# `insert` puts one element before the index, and clamps an index that is off
# either end rather than refusing it.
xs = [1, 2]
print(show(xs, lambda: xs.insert(0, 0)), show(xs, lambda: xs.insert(99, 9)))
xs = [1, 2]
print(show(xs, lambda: xs.insert(-1, 0)), show(xs, lambda: xs.insert(-99, 9)))
xs = []
print(show(xs, lambda: xs.insert(5, 1)), show(xs, lambda: xs.insert(-5, 0)))

# `pop` takes one out and gives it back, from the end by default, and counts
# from the end for a negative index. This one refuses an index that is off the
# end, which is the whole of the difference between it and `insert`.
xs = [1, 2, 3]
print(show(xs, lambda: xs.pop()), show(xs, lambda: xs.pop(0)))
xs = [1, 2, 3]
print(show(xs, lambda: xs.pop(-2)), show(xs, lambda: xs.pop(True)))
xs = [1]
print(caught(lambda: xs.pop(1)), caught(lambda: xs.pop(-2)), xs)
xs = []
print(caught(lambda: xs.pop()), caught(lambda: xs.pop(0)), caught(lambda: xs.pop(99)))

# `remove` takes out the first one that matches and complains if there is none.
xs = [1, 2, 1]
print(show(xs, lambda: xs.remove(1)), show(xs, lambda: xs.remove(1)))
xs = [1]
print(caught(lambda: xs.remove(2)), caught(lambda: xs.remove("1")), xs)

# `clear`, `copy` and `reverse`. The copy is one level deep, so the inner list
# is the same object in both.
xs = [1, [2]]
copied = xs.copy()
print(copied, copied is xs, copied[1] is xs[1])
copied.append(3)
print(xs, copied)
print(show(xs, lambda: xs.clear()), [].copy(), [1, 2, 3].copy())
xs = [1, 2, 3]
print(show(xs, lambda: xs.reverse()), [].reverse(), [1].reverse())

# `count` and `index` compare by identity first and then by equality, which is
# how a NaN in a list is found at all.
nan = 1e400 - 1e400
xs = [nan, 1, nan]
print(xs.count(nan), xs.index(nan), nan == nan)
print([1, 2, 1].count(1), [1, 2, 1].count(3), [].count(1))
print([True, 1, 1.0].count(1), [0, False].count(False))
print([1, 2, 1].index(1), [1, 2, 1].index(2), [1, 2, 1].index(1, 1))

# `index` clamps its start and its stop instead of refusing them, both ends
# and both signs.
xs = [1, 2, 3, 2]
print(xs.index(2, 2), xs.index(2, -3), xs.index(2, 0, 99), xs.index(1, -99))
print(caught(lambda: xs.index(2, 2, 2)), caught(lambda: xs.index(9)))
print(caught(lambda: xs.index(1, 1)), caught(lambda: xs.index(2, 0, 1)))

# `sort` sorts in place and gives back `None`, which is the whole of the
# difference between it and `sorted`.
xs = [3, 1, 2]
print(show(xs, lambda: xs.sort()), sorted([3, 1, 2]))
xs = [3, 1, 2]
print(show(xs, lambda: xs.sort(reverse=True)))
xs = ["bb", "a", "ccc"]
print(show(xs, lambda: xs.sort(key=len)))
xs = [-3, 1, -2]
print(show(xs, lambda: xs.sort(key=abs, reverse=True)))
xs = []
print(show(xs, lambda: xs.sort()), show(xs, lambda: xs.sort(key=abs)))

# Equal elements come out in the order they went in, and `reverse=True` does
# not change that.
xs = [(1, "a"), (0, "b"), (1, "c"), (0, "d")]


def first(pair):
    """The half of a pair the sorts below rank by."""
    return pair[0]


print(show(xs, lambda: xs.sort(key=first)))
xs = [(1, "a"), (0, "b"), (1, "c"), (0, "d")]
print(show(xs, lambda: xs.sort(key=first, reverse=True)))

# The list is empty for the duration of the sort, so a key that looks at it
# sees nothing there.
seen = []
xs = [2, 1]


def looking(value):
    """A key that records what the list looked like when it was called."""
    seen.append(list(xs))
    return value


print(show(xs, lambda: xs.sort(key=looking)), seen)

# A key that adds to the list being sorted has the sort refused, and the
# sorted elements are still put back.
xs = [2, 1]


def meddling(value):
    """A key that puts something in the list it is sorting."""
    xs.append(value)
    return value


print(caught(lambda: xs.sort(key=meddling)), xs)

# A key that raises leaves the list exactly as it was found.
xs = [2, 1, 3]


def raising(value):
    """A key that refuses one of the elements."""
    if value == 3:
        raise ValueError("no")
    return value


print(caught(lambda: xs.sort(key=raising)), xs)
xs = [1, "a"]
print(caught(lambda: xs.sort()), xs)

# The wording, which is not uniform and which a program can read. The ones
# written one way name the type and the ones written the other do not.
xs = [1]
print(caught(lambda: xs.append()), caught(lambda: xs.append(1, 2)))
print(caught(lambda: xs.append(x=1)), caught(lambda: xs.append(1, x=2)))
print(caught(lambda: xs.extend()), caught(lambda: xs.extend([1], [2])))
print(caught(lambda: xs.remove()), caught(lambda: xs.count(1, 2)))
print(caught(lambda: xs.count(x=1)), caught(lambda: xs.remove(1, 2)))
print(caught(lambda: xs.clear(1)), caught(lambda: xs.reverse(1, 2)))
print(caught(lambda: xs.copy(1)), caught(lambda: xs.clear(x=1)))
print(caught(lambda: xs.insert(1)), caught(lambda: xs.insert(1, 2, 3)))
print(caught(lambda: xs.insert()), caught(lambda: xs.insert(1, 2, x=3)))
print(caught(lambda: xs.pop(1, 2)), caught(lambda: xs.pop(x=1)))
print(caught(lambda: xs.index()), caught(lambda: xs.index(1, 2, 3, 4)))
print(caught(lambda: xs.index(1, x=2)), caught(lambda: xs.sort(1)))
print(caught(lambda: xs.sort(foo=1)), caught(lambda: xs.sort(key=abs, foo=1)))

# An index has to be an integer, and one too big for a machine word is refused
# where it is used to reach an element and taken as far as it goes where it is
# used as a bound.
print(caught(lambda: xs.pop("a")), caught(lambda: xs.insert("a", 1)))
print(caught(lambda: xs.pop(1.0)), caught(lambda: xs.insert(None, 1)))
print(caught(lambda: xs.pop(2**70)), caught(lambda: xs.insert(2**70, 1)))
print(caught(lambda: xs.index(1, 2**70)), caught(lambda: xs.index(1, 0, 2**70)))
print(caught(lambda: xs.index(1, -(2**70))), caught(lambda: xs.index(1, "a")))
print(xs)

# A name a list has not got is an `AttributeError`, and it says which type.
print(caught(lambda: xs.nope))
print(caught(lambda: xs.push(1)))
print(caught(lambda: [].sorted))
