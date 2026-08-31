"""A module for `imports.py` to import.

Named with a leading underscore because the runner treats those as helpers
rather than cases, which is the same thing as saying they are imported and not
run. Everything in here exists to be reached from somewhere else.
"""

GREETING = "hello"
WHOSE = "greeting"

# Run at import time rather than assigned, so that a runtime which hands over a
# half built module gets caught: this is only right if the body finished.
LOUD = GREETING.upper()


def greet(name):
    """Reads a global that belongs to this module and not to the caller's.

    `WHOSE` is bound in the importing module too, to a different value, and at
    a different index in its name table. A runtime that resolves globals by
    index without tracking which module a body came from returns the caller's.
    """
    return GREETING + ", " + name + ", from " + WHOSE


def rebound():
    """The same global again, so a caller can see an assignment to it land."""
    return GREETING


def squares(n):
    """A generator, which stops and starts rather than running to the end.

    Stepping it from another module means crossing a module boundary once per
    value, in and out, which is the arrangement a plain call never produces.
    """
    for i in range(n):
        yield i * i, WHOSE
