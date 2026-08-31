"""What a dictionary knows how to do, and what its three views are.

The views are the half worth writing a case for. They are windows onto the
dictionary and not copies of its contents, so an entry added after the view was
bound is in the view, and a runtime that got that wrong would pass every check
that only looked at a view straight after taking it.

`fromkeys` is not here. It is called on the type rather than on a dictionary,
which is a different lookup, and the suite covers it when there is one.
"""

d = {"b": 2, "a": 1, "c": 3}

# The three views, and the fact that they print as themselves rather than as
# the lists they are not.
print(d.keys(), d.values(), d.items())
print(len(d.keys()), len(d.values()), len(d.items()))
print(list(d.keys()), list(d.values()), list(d.items()))
print(sorted(d.keys()), sorted(d.values()), sorted(d.items()))

# Walking the dictionary and walking its keys give the same thing, in the same
# order, which is insertion order and not sorted order.
print([k for k in d], [k for k in d.keys()])
for key, value in d.items():
    print("pair", key, value)

# `in` asks each view about a different thing.
print("a" in d.keys(), "z" in d.keys())
print(1 in d.values(), 9 in d.values())
print(("a", 1) in d.items(), ("a", 9) in d.items())
# Something that is not a pair at all is not in there, and is not an error.
print("a" in d.items(), ("a", 1, 2) in d.items())

# Empty is false, like every other container.
print(bool({}.keys()), bool({}.values()), bool({}.items()), bool(d.keys()))

# A view is a window. Bind one, change the dictionary, and the view has the
# change. This is the whole difference from Python 2 and it is why a view is
# worth having.
ks = d.keys()
vs = d.values()
its = d.items()
d["e"] = 5
print(ks, vs, its)
print(len(ks), "e" in ks, 5 in vs, ("e", 5) in its)
del d["e"]
print(ks, len(its))

# `get` and `setdefault`, which differ in whether the miss is remembered.
print(d.get("a"), d.get("z"), d.get("z", 0), d)
print(d.setdefault("a", 9), d.setdefault("z", 9), d)

# `pop` with a default and without: the missing key is the default in one and a
# KeyError in the other, and the KeyError carries the key itself.
print(d.pop("z"), d.pop("z", "gone"))

# `popitem` takes the last entry, not an arbitrary one. It has been the last
# one since 3.7 and programs use it as a stack.
print(d.popitem(), d)

# `copy` is shallow, like every copy in the language.
nested = {"xs": [1, 2]}
shallow = nested.copy()
shallow["xs"].append(3)
shallow["new"] = 1
print(nested, shallow)

# `update` takes four shapes, and the keywords are applied after whatever came
# in positionally, so they win.
e = {}
e.update({"a": 1})
e.update([("b", 2)])
e.update({"c": 3}.items())
e.update(dd=4)
e.update({"f": 5}, f=6)
print(e)
e.clear()
print(e, len(e), bool(e))


def check(label, work):
    try:
        print(label, "->", work())
    except TypeError as e:
        print(label, "-> TypeError:", e)
    except ValueError as e:
        print(label, "-> ValueError:", e)
    except KeyError as e:
        print(label, "-> KeyError:", e)
    except AttributeError as e:
        print(label, "-> AttributeError:", e)


# The mistakes. CPython names the type in some of these and not in others,
# depending on which half of its own source the method is written in, and a
# program can see the difference.
g = {"a": 1}
check("get()", lambda: g.get())
check("get(1, 2, 3)", lambda: g.get(1, 2, 3))
check("setdefault()", lambda: g.setdefault())
check("pop()", lambda: g.pop())
check("pop(missing)", lambda: g.pop("z"))
check("copy(1)", lambda: g.copy(1))
check("clear(1)", lambda: g.clear(1))
check("popitem(1)", lambda: g.popitem(1))
check("popitem on empty", lambda: {}.popitem())
check("keys(1)", lambda: g.keys(1))
check("values(1)", lambda: g.values(1))
check("items(1)", lambda: g.items(1))
check("update(a, b)", lambda: g.update({}, {}))
check("update(3)", lambda: g.update(3))
check("update triple", lambda: g.update([("a", 1, 2)]))
check("update short", lambda: g.update([("a",)]))
check("update ints", lambda: g.update([1, 2]))
check("nosuchmethod", lambda: g.nosuchmethod)
check("view nosuchmethod", lambda: g.keys().nosuchmethod)

# An unhashable key is an error and not a False, because the question went to a
# hash table and never reached a comparison. The two type names in the message
# need not be the same one: the first is what was handed over and the second is
# what inside it refused.
check("[] in keys", lambda: [] in g.keys())
check("([], 1) in items", lambda: ([], 1) in g.items())
check("[] in values", lambda: [] in g.values())
check("get([])", lambda: g.get([]))
check("get(([], 1))", lambda: g.get(([], 1)))

# A dict_values is not set-like, because values need be neither unique nor
# hashable, so this is an ordinary unsupported operand rather than a set
# operation.
check("values() & set", lambda: g.values() & {1})
check("values().isdisjoint", lambda: g.values().isdisjoint({1}))

# The set operators want an iterable on the other side, and something that is
# not one is refused before anything is intersected.
check("keys() & 1", lambda: g.keys() & 1)
check("keys() & None", lambda: g.keys() & None)
check("keys() <= list", lambda: g.keys() <= ["a"])

# A view compared with something that is not set-like at all is just false.
print(g.keys() == 1, g.values() == g.values(), g.items() == "a")
