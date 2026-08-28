"""Generator close, throw, and the finally-during-teardown path.

The interaction between `yield` inside `try/finally` and generator collection
is one of the places runtimes reliably diverge.
"""


def gen():
    try:
        yield 1
        yield 2
    except ValueError as exc:
        print("caught inside:", exc)
        yield 99
    finally:
        print("finally ran")


g = gen()
print(next(g))
print(g.throw(ValueError("boom")))
g.close()

g2 = gen()
print(next(g2))
del g2  # finally must run at collection


def delegating():
    result = yield from gen()
    print("delegated result", result)


d = delegating()
print(next(d))
print(next(d))
try:
    next(d)
except StopIteration:
    print("StopIteration")
