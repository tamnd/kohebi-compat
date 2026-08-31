"""The type of a value, as a value.

The identity is the half worth writing a case for. A runtime that built a fresh
type object on every ask would print exactly the same thing as one that hands
back the same object every time, and would fail every program that writes
`type(x) is int`. So most of what is below is `is` rather than `==`.

The constructors are not here. `int`, `float`, `dict`, `bytes` and `object` are
names bound to types whose constructors are a separate piece of work, and the
suite covers them when there are some.
"""


class Animal:
    pass


class Dog(Animal):
    pass


def gen():
    yield 1


# What a value says it is. The names with no module in front of them are the
# only ones here, because CPython gives a type a dotted name for its repr and a
# bare one everywhere else, and the two differ only for a type that lives in a
# module.
print(type(1), type(True), type(1.5), type("a"), type(b"a"))
print(type([]), type(()), type({}), type(set()), type(None))
print(type(range(3)), type(print), type(iter([])), type(gen()))
print(type({}.keys()), type({}.values()), type({}.items()))
print(type(map(str, [])), type(filter(None, [])), type(...))

# The type of a class is `type`, whichever of the three kinds of class it is.
print(type(int), type(ValueError), type(Dog), type(type))

# A class written in Python prints with the module it was written in.
print(Dog, type(Dog()), type(Dog()) is Dog)

# One object per type, for the whole run. The second half is the point: a type
# with no name to be bound to still gets one object rather than one per ask.
print(type(1) is int, type([]) is list, type(1) is str)
print(type(None) is type(None), type(gen()) is type(gen()))
print(type(iter([])) is type(iter([1])), int is int, type(type) is type)

# `__name__` is how a program prints what it caught, and it works on all three
# kinds of class.
print(type(1).__name__, type(None).__name__, ValueError.__name__)
print(Dog.__name__, type.__name__, object.__name__)

# A type is a value like any other: true, comparable, hashable, printable.
print(bool(int), int == int, type(1) == int, type(1) != str)
print({int: "a", str: "b"}[int], [int, str].index(str))

# What derives from what. This is the whole graph: the exception tree, `bool`
# under `int`, a class's chain of bases, and `object` over all of it.
print(isinstance(True, int), isinstance(1, bool), isinstance(1, object))
print(isinstance(None, object), isinstance("a", str), isinstance(1, float))
print(isinstance(ValueError("x"), ValueError), isinstance(ValueError("x"), Exception))
print(isinstance(ValueError("x"), BaseException), isinstance(ValueError("x"), TypeError))
print(isinstance(int, type), isinstance(int, object), isinstance(ValueError, type))
d = Dog()
print(isinstance(d, Dog), isinstance(d, Animal), isinstance(d, object), isinstance(d, int))

print(issubclass(bool, int), issubclass(int, bool), issubclass(int, int))
print(issubclass(int, object), issubclass(type, object), issubclass(object, object))
print(issubclass(ValueError, Exception), issubclass(Exception, ValueError))
print(issubclass(Dog, Animal), issubclass(Animal, Dog), issubclass(Dog, object))

# The second argument may be a tuple, and unlike an `except` clause it may hold
# tuples of its own. An empty one catches nothing, which is not an error.
print(isinstance(1, (str, int)), isinstance(1, (str, float)), isinstance(1, ()))
print(isinstance(1, ((str,), (int,))), issubclass(int, (str, int)), issubclass(int, ()))


def check(label, work):
    try:
        print(label, "->", work())
    except TypeError as e:
        print(label, "-> TypeError:", e)
    except AttributeError as e:
        print(label, "-> AttributeError:", e)


# Neither question takes a keyword, and both count before they look at
# anything, so a wrong count complains about the count and not about the value.
check("isinstance(1)", lambda: isinstance(1))
check("isinstance(1, 2, 3)", lambda: isinstance(1, 2, 3))
check("isinstance(x=1)", lambda: isinstance(x=1))
check("issubclass(int)", lambda: issubclass(int))
check("issubclass(int, int, int)", lambda: issubclass(int, int, int))

# A second argument that is not a class, which the two word differently, and a
# first argument to `issubclass` that is not one, which only it can refuse.
check("isinstance(1, 2)", lambda: isinstance(1, 2))
check("isinstance(1, (2,))", lambda: isinstance(1, (2,)))
check("isinstance(1, None)", lambda: isinstance(1, None))
check("issubclass(int, 1)", lambda: issubclass(int, 1))
check("issubclass(1, int)", lambda: issubclass(1, int))
check("issubclass(Dog(), Dog)", lambda: issubclass(Dog(), Dog))

# `type` takes one argument or three, and nothing else, including no keyword.
check("type()", lambda: type())
check("type(1, 2)", lambda: type(1, 2))
check("type(x=1)", lambda: type(x=1))

# A name a type does not have is the AttributeError a type gives rather than
# the one a value gives, and the two are worded differently. Only the class
# side is here: `(1).nosuch` is the other wording and it goes in whenever `int`
# has a table of methods to look the name up in and miss.
check("int.nosuch", lambda: int.nosuch)
check("ValueError.nosuch", lambda: ValueError.nosuch)
check("Dog.nosuch", lambda: Dog.nosuch)
check("type(None).nosuch", lambda: type(None).nosuch)
