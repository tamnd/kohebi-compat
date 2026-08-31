"""A module that imports another one, so an import can be transitive.

It also keeps state at module level and changes it, which is the thing that
distinguishes a module from a copy of a module: two importers reach the same
counter, not one each.
"""

import _greeting

COUNT = 0
WHOSE = "counter"


def bump():
    """Rebinds a global in this module, which a `global` statement is for."""
    global COUNT
    COUNT = COUNT + 1
    return COUNT


def through(name):
    """A call that crosses two module boundaries rather than one."""
    return _greeting.greet(name) + " via " + WHOSE
