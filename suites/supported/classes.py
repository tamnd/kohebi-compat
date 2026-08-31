"""Classes: the body, the namespace it fills, and what a method can see.

A class body is not an ordinary frame, and most of what is here is about the
ways it differs. Its names go into a namespace rather than into slots, it is
not an enclosing scope for the functions defined in it, and a name it binds is
its own even where an enclosing function has one too.

Single inheritance only, and nothing here reads a dunder the runtime would have
to call, because `__repr__`, `__eq__`, `__len__` and `__bool__` are user code
called from inside an operation that cannot call anything yet.
"""


class Point:
    kind = "point"

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def sum(self):
        return self.x + self.y

    def scaled(self, by):
        return Point(self.x * by, self.y * by)


p = Point(1, 2)
print(p.x, p.y, p.kind, p.sum())
print(p.scaled(10).sum())

# An attribute set on the instance shadows the one on the class, and deleting
# it uncovers the class one again rather than leaving a hole.
p.kind = "mine"
print(p.kind, Point.kind)
del p.kind
print(p.kind)

# The same on the class itself, which every instance sees at once.
Point.kind = "moved"
print(Point(0, 0).kind)


# A method is the function the lookup found with the receiver bound to it, so
# calling it through the class and passing the receiver by hand is the same
# call.
print(Point.sum(p))
print(p.sum())


# Single inheritance: what the subclass does not define, it gets.
class Shifted(Point):
    def __init__(self, x, y, by):
        Point.__init__(self, x, y)
        self.by = by

    def sum(self):
        return Point.sum(self) + self.by


s = Shifted(1, 2, 100)
print(s.sum(), s.x, s.kind)


# A class body is not an enclosing scope for the functions in it. The bare name
# is not found, and `self.` is how it has to be written.
class Bare:
    value = 41

    def read(self):
        return self.value


try:

    class Broken:
        value = 41

        def read(self):
            return value

    Broken().read()
except NameError:
    print("a bare name in a method is not the class attribute")

print(Bare().read())


# A name the body binds is the body's own, even where an enclosing function has
# one. So this reads the module's `outside` and not the function's.
outside = "module"


def enclosing():
    outside = "function"

    class Reader:
        seen = outside

    return Reader.seen, outside


print(enclosing())


# A `global` in a class body takes the name out of the namespace, so it is not
# an attribute of the class afterwards.
total = 0


class Adder:
    global total
    total = 7
    kept = 8


print(total, Adder.kept)
try:
    Adder.total
except AttributeError:
    print("a global in the body is not an attribute")


# A body that raises builds no class, and the name stays unbound.
try:

    class Fails:
        raise ValueError("in the body")

except ValueError:
    print("the body raised")
try:
    Fails
except NameError:
    print("and bound nothing")


# The name a method is called wrongly by is the qualified one.
try:
    p.sum(1)
except TypeError:
    print("the arity of a method counts the receiver")


# A base that is not a class is refused rather than half accepted.
try:

    class FromAnInt(1):
        pass

except TypeError:
    print("a base has to be a class")


# What a missing attribute says depends on which of the two kinds was asked.
try:
    p.nothing
except AttributeError:
    print("no such attribute on an instance")
try:
    Point.nothing
except AttributeError:
    print("no such attribute on a class")
