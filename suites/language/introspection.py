"""Frame introspection and sys.settrace.

These are the features that make aggressive optimisation hard, and a runtime
that skips them fails on debuggers, coverage tools, and pytest.
"""

import sys


def target(n):
    total = 0
    for i in range(n):
        total += i
    return total


def tracer(frame, event, arg):
    if frame.f_code.co_name == "target" and event == "call":
        print("call", frame.f_code.co_name, "argcount", frame.f_code.co_argcount)
    return None


sys.settrace(tracer)
print(target(5))
sys.settrace(None)


def caller():
    frame = sys._getframe(1)
    return frame.f_code.co_name


def outer():
    return caller()


print(outer())
print(target.__code__.co_varnames)
