"""Generators: suspension, resumption, and where the value goes at the end.

The subset kohebi implements is plain `yield`, the generator object, `next`,
iteration under `for`, and the value a `return` puts on the `StopIteration`.
`send`, `close`, `throw` and `yield from` are not here, because they are not
there.

Nothing here reads an attribute of the exception it catches or calls `list` on
a generator, for the same reason: an attribute of anything that is not a class
or an instance of one has nowhere to be looked up yet, and `list` is a type and
types are what that is waiting on. A comprehension is what collects a generator
in here instead.
"""


def count(n):
    i = 0
    while i < n:
        yield i
        i = i + 1


# Calling one runs none of the body. Everything below the print in `announce`
# happens after the call, not during it.
def announce():
    print("body started")
    yield 1


g = announce()
print("called")
print(next(g))

# The frame is the whole of the state, so the loop counter is still counting
# after each suspension hands control back.
for x in count(4):
    print(x)

print([v * v for v in count(5)])

# A generator is its own iterator, so a `for` over a half consumed one carries
# on rather than starting again.
half = count(4)
print(iter(half) is half)
print(next(half))
for x in half:
    print("rest", x)


# What a generator returns ends it, and it is over afterwards, so the second
# ask finds nothing rather than the same thing again.
def returns():
    yield "only"
    return "the value"


done = returns()
print(next(done))
try:
    next(done)
except StopIteration:
    print("first")
try:
    next(done)
except StopIteration:
    print("again")

# A default swallows the end and everything it carried.
print(next(returns(), "default"))
print(next(count(0), "empty"))


# A `for` loop discards what the generator returned rather than raising it.
for x in returns():
    print("loop", x)
print("after the loop")


# A `return` in front of a `yield` is how an empty generator is written, and
# the `yield` is what makes it one at all.
def never():
    return
    yield


print([v for v in never()])


# The locals a generator suspends over include the cells it captured.
def counter():
    total = 0

    def bump(by):
        nonlocal total
        total = total + by
        return total

    yield bump(1)
    yield bump(10)
    yield bump(100)


print([v for v in counter()])


# One generator walking another, which is what `yield from` will shorten and
# what it is defined in terms of.
def doubled(n):
    for v in count(n):
        yield v * 2


print([v for v in doubled(4)])


# Unpacking walks it, and walking it too far says how far it got.
a, b = count(2)
print(a, b)
try:
    c, d = count(1)
except ValueError:
    print("not enough values")


# A generator that raises is over. The exception leaves the frame the way it
# leaves any other frame, and asking again finds nothing.
def raises():
    yield "before"
    raise ValueError("from inside")


boom = raises()
print(next(boom))
try:
    next(boom)
except ValueError:
    print("caught")
print(next(boom, "over"))


# A `finally` runs when the body reaches it, which under a `for` is when the
# generator falls off its end.
def guarded():
    try:
        yield 1
        yield 2
    finally:
        print("cleanup")


for x in guarded():
    print(x)


# A handler that a `yield` suspends inside is still the handler when the
# generator comes back to it.
def handles():
    try:
        raise ValueError("inner")
    except ValueError:
        yield "in the handler"
        yield "still in it"
    yield "out of it"


print([v for v in handles()])


# Arguments are bound when the generator is called, before anything runs, so a
# call with the wrong number of them fails at the call.
def one(a):
    yield a


try:
    one(1, 2)
except TypeError:
    print("wrong arity")


# A generator asking for its own next value finds itself already running.
def eats_itself():
    yield next(self_eater)


self_eater = eats_itself()
try:
    next(self_eater)
except ValueError:
    print("already executing")


# The repr names the body the way it was qualified, so a method reads as `C.f`
# and one written inside a function as `outer.<locals>.inner`. The address in
# it is the one thing the normaliser rewrites, and the name in front of it is
# what these two lines are for.
class C:
    def method(self):
        yield 1


def outer():
    def inner():
        yield 1

    return inner()


print(C().method())
print(outer())
