"""`sys.stdout` and `sys.stderr`, and the fact that they are two places.

The runner captures the two separately and compares both, which is what makes
this case worth writing: a runtime that folded them into one sink would print
every line here and still fail, because the lines would all be on the same
side.

The attributes checked are the ones that depend on nothing but the runtime.
`encoding` and `errors` are here because the runner sets `PYTHONIOENCODING`, so
the oracle is not reading a locale. `line_buffering` and `write_through` are
not, because both depend on whether the stream is a terminal, which is a fact
about how the suite was invoked rather than about the language.
"""

import sys

# The two go to two places, four ways of getting there.
print("out: print")
print("err: print", file=sys.stderr)
sys.stdout.write("out: write\n")
sys.stderr.write("err: write\n")
print("out: explicit file=None", file=None)

# `write` gives back a count of characters. Not of bytes, which is a different
# number the moment anything needs more than one.
print(sys.stdout.write("out: counted\n"))
print(sys.stdout.write("é\U0001f600ab"), sys.stdout.write("\n"))

# `writelines` puts nothing between the elements, which surprises people and is
# what the method does.
sys.stdout.writelines(["a", "b", "c"])
sys.stdout.writelines(["\n"])

# `flush` gives back nothing and is allowed to be called on either.
print(sys.stdout.flush(), sys.stderr.flush())

# What a stream says about itself.
print(sys.stdout)
print(sys.stderr)
print(repr(sys.stdout.name), repr(sys.stderr.name), repr(sys.stdout.mode))
print(repr(sys.stdout.encoding), repr(sys.stdout.errors), repr(sys.stderr.errors))
print(sys.stdout.closed, sys.stdout.writable(), sys.stdout.readable())
print(repr(sys.stdout.newlines))

# The same object every time, which is what lets a program stash one and
# compare it later.
print(sys.stdout is sys.stdout, sys.stdout is sys.stderr)
saved = sys.stdout
print(saved is sys.stdout)

# The mistakes, and what each of them is called.
try:
    sys.stdout.write(1)
except TypeError as e:
    print("TypeError:", e)
try:
    sys.stdout.write(None)
except TypeError as e:
    print("TypeError:", e)
try:
    sys.stdout.write("a", "b")
except TypeError as e:
    print("TypeError:", e)
try:
    sys.stdout.flush(1)
except TypeError as e:
    print("TypeError:", e)
try:
    sys.stdout.writelines(1)
except TypeError as e:
    print("TypeError:", e)
try:
    sys.stdout.nosuchthing
except AttributeError as e:
    print("AttributeError:", e)

# `writelines` writes as it goes, so what is in front of the bad element is
# already out before the complaint arrives.
try:
    sys.stderr.writelines(["err: partial ", "write ", 1, "never"])
except TypeError as e:
    print("TypeError:", e)
print("", file=sys.stderr)
