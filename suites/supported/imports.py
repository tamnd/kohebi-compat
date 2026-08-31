"""Imports, and the thing underneath them that is easy to get wrong.

An import is two pieces. Finding a file and running it is the visible one. The
other is that a function carries the module it was written in: the globals it
reads belong to that module, not to whoever called it, and a runtime that
numbers globals by index has to keep those numbers apart per module or a call
across a boundary reads the wrong slot. Every case here that binds the same
name in two modules is aiming at that.

Nothing in here prints a path. `__file__` and the origin in an `ImportError`
are both absolute and both differ between machines, so what gets printed is
whether they look right rather than what they say.
"""

import _counter
import _greeting
import _greeting as same
import sys
from _counter import bump
from _greeting import GREETING, greet
from _greeting import WHOSE as THEIRS

# Bound here too, to something else. Every call below that reads `WHOSE` inside
# an imported function has to see that module's, not this line.
WHOSE = "importer"

print(_greeting.GREETING, _greeting.LOUD, _greeting.WHOSE)
print(_greeting.__name__, _counter.__name__, sys.__name__)

# The name a module was bound to is a name for the same object, however many
# ways it was asked for. `as` does not copy anything.
print(same is _greeting, GREETING is _greeting.GREETING)
print(THEIRS, WHOSE, THEIRS == WHOSE)

# The call that reads its own module's globals, four ways round: through the
# module, through a name imported from it, through a module that imports it,
# and from inside a comprehension in this one.
print(_greeting.greet("a"))
print(greet("b"))
print(_counter.through("c"))
print([greet(who) for who in ["d", "e"]])

# The state in an imported module is one thing rather than one per importer,
# which is what `sys.modules` being a registry means.
print(bump(), bump(), _counter.bump(), _counter.COUNT)

# An assignment to a module attribute is an assignment to that module's global,
# so the function defined in it sees the new value. Two copies of a namespace
# would print the old one here.
_greeting.GREETING = "goodbye"
print(_greeting.rebound(), _greeting.greet("f"))
_greeting.GREETING = "hello"
print(_greeting.rebound())

# A generator defined elsewhere and stepped from here, which crosses the
# boundary once per value rather than once per call.
walk = _greeting.squares(4)
print(next(walk), next(walk))
print([pair for pair in walk])
print([pair for pair in _greeting.squares(3)], WHOSE)


def local_import():
    """An import inside a function binds a local, not a global."""
    import _greeting as inner

    return inner.WHOSE


print(local_import(), WHOSE)

# `sys.modules` is the registry itself, so what is in it is what has been
# imported, and importing something already there is a lookup rather than a run.
print("_greeting" in sys.modules, "_counter" in sys.modules, "sys" in sys.modules)
print(sys.modules["_greeting"] is _greeting)
print("__main__" in sys.modules, sys.modules["__main__"].__name__)

# The script is `__main__` and has a file, and an imported module is itself and
# has one too. The paths differ between machines, so this asks the shape.
print(__name__, __file__.endswith("imports.py"))
print(_greeting.__name__, _greeting.__file__.endswith("_greeting.py"))

# `sys.argv` is the program's arguments. Run with none, it is the script alone.
print(len(sys.argv), sys.argv[1:])

# A module nothing answers to, and the two halves of a dotted name that has no
# package to resolve against. These are three different mistakes and CPython
# words them differently.
try:
    import nosuchmodule
except ModuleNotFoundError as e:
    print("ModuleNotFoundError:", e)
try:
    import nosuchpackage.inside
except ModuleNotFoundError as e:
    print("ModuleNotFoundError:", e)
try:
    import _greeting.inside
except ModuleNotFoundError as e:
    print("ModuleNotFoundError:", e)

# A name a module has not got, asked for both ways round. The attribute error
# says it all; the import error names the file it looked in, which is a path,
# so only its first half is printed.
try:
    _greeting.absent
except AttributeError as e:
    print("AttributeError:", e)
try:
    from _greeting import absent
except ImportError as e:
    print("ImportError:", str(e).split(" (")[0])
