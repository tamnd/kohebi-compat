"""What a set knows how to do.

Every answer that is a set goes through `sorted` before it is printed. A set
has no order the language promises, and CPython's own order is a fact about its
hash table rather than about the program, so a case that printed a set with
more than one member in it would be testing an implementation detail. The
single member ones are printed as themselves, because there is only one order
those can be in.

The methods and the operators are deliberately both here. They do not accept
the same things, and a runtime that implemented one in terms of the other would
pass half of this and fail the other half.
"""

s = {1, 2, 3}

# The four operations, in the form that gives back a new set. Each takes any
# number of iterables, not just sets, and not just one.
print(sorted(s.union([4], (5,), {6: "x"})))
print(sorted(s.intersection([1, 2], [2, 3])))
print(sorted(s.difference([1], [2])))
print(sorted(s.symmetric_difference([3, 4])))

# With no arguments at all, three of them are a copy.
print(sorted(s.union()), sorted(s.intersection()), sorted(s.difference()))

# The three questions, which also take any iterable.
print(s.issubset([1, 2, 3, 4]), s.issubset([1]), s.issubset(s))
print(s.issuperset([1]), s.issuperset([9]), s.issuperset(s))
print(s.isdisjoint([9]), s.isdisjoint([1]), s.isdisjoint(""))

# A string is an iterable of its characters, which is what the methods see.
print(sorted({"a", "z"}.union("bc")), {"a"}.isdisjoint("abc"))

# A dict is an iterable of its keys.
print(sorted({1}.union({2: "x", 3: "y"})))

# `copy` is shallow and is not the same object.
print(sorted(s.copy()), s.copy() is s, s.copy() == s)

# The same four again, in the form that changes the set it was called on. Each
# gives back nothing.
t = {1, 2, 3}
print(t.update([4], (5,)), sorted(t))
print(t.intersection_update([1, 2, 4, 5], [2, 4, 5]), sorted(t))
print(t.difference_update([4]), sorted(t))
print(t.symmetric_difference_update([2, 9]), sorted(t))

# Reading the argument happens before anything is written, so a set updated
# from itself works rather than complaining about a set that moved.
u = {1, 2}
u.update(u)
print(sorted(u))
u.intersection_update(u)
print(sorted(u))

# Adding and taking away one member at a time. `discard` does not mind a
# member that was never there and `remove` does.
v = {1, 2}
print(v.add(3), sorted(v))
print(v.discard(9), v.discard(3), sorted(v))
print(v.remove(1), sorted(v))
print(v.pop(), sorted(v))
print(v.clear(), v, len(v), bool(v))

# An empty set prints as a call, because `{}` is a dict.
print(set(), sorted(set()), bool(set()), len(set()))

# A set changed while it is being walked is caught. The sentence has a capital
# letter on it, which is not how the same complaint about a dictionary is
# spelled.
try:
    walked = {1}
    for member in walked:
        walked.add(member + 1)
except RuntimeError as e:
    print("RuntimeError:", e)


def check(label, work):
    try:
        print(label, "->", work())
    except TypeError as e:
        print(label, "-> TypeError:", e)
    except KeyError as e:
        print(label, "-> KeyError:", e)
    except AttributeError as e:
        print(label, "-> AttributeError:", e)


# An operator wants a set on both sides where the method takes any iterable.
# This is the difference a runtime is most likely to smooth over, and CPython
# keeps it on purpose: an operator between two kinds of container is far more
# often a mistake than an intention.
g = {1, 2, 3}
print(sorted(g | {4}), sorted(g & {2}), sorted(g - {1}), sorted(g ^ {3, 4}))
check("set | list", lambda: g | [4])
check("set & str", lambda: g & "a")
check("set - dict", lambda: g - {4: "x"})
print(sorted(g.union([4])), sorted(g.intersection("")), sorted(g.difference([1])))

# The counts, which CPython words three different ways in three neighbouring
# methods.
check("add()", lambda: g.add())
check("add(1, 2)", lambda: g.add(1, 2))
check("add(x=1)", lambda: g.add(x=1))
check("clear(1)", lambda: g.clear(1))
check("clear(x=1)", lambda: g.clear(x=1))
check("copy(1)", lambda: g.copy(1))
check("pop(1)", lambda: g.pop(1))
check("isdisjoint()", lambda: g.isdisjoint())
check("isdisjoint(a, b)", lambda: g.isdisjoint([1], [2]))
check("symdiff(a, b)", lambda: g.symmetric_difference([1], [2]))
check("sdu(a, b)", lambda: g.symmetric_difference_update([1], [2]))
check("union(x=1)", lambda: g.union(x=1))

# A missing member, an empty set, and a name that is not a method.
check("remove(9)", lambda: g.remove(9))
check("pop on empty", lambda: set().pop())
check("nosuchmethod", lambda: g.nosuchmethod)

# An argument that is not iterable at all.
check("isdisjoint(1)", lambda: g.isdisjoint(1))
check("issubset(1)", lambda: g.issubset(1))
check("update(1)", lambda: g.update(1))
check("union(1)", lambda: g.union(1))

# An unhashable element gets one of two messages, and which one depends on the
# method rather than on the element. The three that give the short one build a
# whole set out of the argument before looking at it, so the value loses track
# of what it was going to be used for on the way in.
check("difference", lambda: g.difference([[]]))
check("difference_update", lambda: g.difference_update([[]]))
check("symmetric_difference", lambda: g.symmetric_difference([[]]))
check("symmetric_difference_update", lambda: g.symmetric_difference_update([[]]))
check("union", lambda: g.union([[]]))
check("update", lambda: g.update([[]]))
check("isdisjoint", lambda: g.isdisjoint([[]]))
check("issuperset", lambda: g.issuperset([[]]))
check("add", lambda: g.add([]))
check("remove", lambda: g.remove([]))
check("discard", lambda: g.discard([]))
check("intersection", lambda: g.intersection([[]]))
check("intersection_update", lambda: g.intersection_update([[]]))
check("issubset", lambda: g.issubset([[]]))

# The two type names in the long message need not be the same one. The first is
# what was handed over and the second is what inside it refused.
check("add tuple with list", lambda: g.add(([], 1)))
check("[] in set", lambda: [] in g)
