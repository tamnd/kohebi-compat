"""Descriptor protocol, including the ordering guarantees.

A runtime that caches attribute lookups too aggressively gets this wrong: the
data descriptor on the type must win over the instance dictionary entry.
"""


class Loud:
    def __set_name__(self, owner, name):
        print("set_name", owner.__name__, name)
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        print("get", self.name)
        return obj.__dict__.get("_" + self.name, "unset")

    def __set__(self, obj, value):
        print("set", self.name, value)
        obj.__dict__["_" + self.name] = value


class Point:
    x = Loud()
    y = Loud()


p = Point()
print(p.x)
p.x = 3
print(p.x)
# The data descriptor wins even though the instance dict has the key.
p.__dict__["x"] = "shadow"
print(p.x)
print(sorted(p.__dict__))
