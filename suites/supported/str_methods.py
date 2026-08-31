"""The methods a string has for searching, splitting and joining.

Nineteen of them, along with what each one does at its edges and what it says
when it is called wrongly. The wording is not uniform and a program can read
all of it, so the refusals are checked as closely as the answers.

A Python string is a sequence of code points rather than of bytes, so `find`
answers in code points and a split cuts on them. There is an emoji in a few of
these for that reason: it is one code point and four bytes, and a runtime that
counted bytes would be off by three.
"""


def caught(thunk):
    """What a call gave back, or what it was refused with."""
    try:
        return repr(thunk())
    except TypeError as e:
        return "TypeError: " + str(e)
    except ValueError as e:
        return "ValueError: " + str(e)
    except AttributeError as e:
        return "AttributeError: " + str(e)


# `find` answers -1 and `index` complains, and `rfind` and `rindex` are the
# same two from the other end.
print("abcabc".find("b"), "abcabc".find("b", 2), "abc".find("z"))
print("abcabc".rfind("b"), "abc".rfind("z"), "abc".find("b", 0, 1))
print(caught(lambda: "abc".index("z")), caught(lambda: "abc".rindex("z")))
print("abc".index("b"), "abc".rindex("b"), "abcabc".index("b", 2))
print(caught(lambda: "abc".index("z", 0, 1)), caught(lambda: "abc".rindex("a", 1)))

# The start is pulled up to zero and the stop is pulled to both ends, which is
# not symmetric and which a program can see. An empty needle is found at the
# start of the window, so `find('', 3)` is 3 and `find('', 4)` is a miss.
print("abc".find(""), "abc".find("", 3), "abc".find("", 4), "abc".find("", 2, 1))
print("abc".rfind(""), "abc".rfind("", 0, 1), "abc".find("c", 0, -1))
print("abcabc".find("b", -2), "abc".find("c", -1), "abc".rfind("a", 1))
print("abc".find("a", None, None), "abc".index("a", None), "abc".find("a", 5, 9))

# `count` counts occurrences that do not overlap, and an empty needle once
# more than there are code points in the window.
print("aaa".count("a"), "aaa".count("aa"), "abc".count(""))
print("abc".count("", 1, 2), "abc".count("", 5), "abc".count("", 2, 1))
print("abcabc".count("b", -3), "abc".count("a", None, 2), "abc".count("a", None, None))

# `startswith` and `endswith` take one string or a tuple of them, and stop at
# the first that matches, so a wrong type after a match is never looked at.
print("abc".startswith("a"), "abc".startswith(("z", "a")), "abc".startswith("b", 1))
print("abc".endswith(("c",)), "abc".endswith("b", 0, 2), "abc".endswith("a", 0, -2))
print("abc".startswith(()), "".startswith(""), "abc".startswith("abcd"))
print("abc".startswith("", 9), "abc".startswith("", 3), "abc".endswith("", 9))
print("abc".startswith("abc", 0, 2), "abc".endswith("c", 5), "abc".startswith("c", -1))
print("abc".startswith(("a", 1)), "abc".startswith("a", None, None))

# `join` walks whatever it is given, so a string, a tuple and a lazy builtin
# are all fine, and every element has to be a string.
print(",".join(["a", "b"]), repr(",".join([])), ",".join("ab"))
print(",".join(("a", "b")), ",".join(map(str, [1, 2])), "abc".join("ab"))
print(caught(lambda: ",".join([1])), caught(lambda: "a".join(["a", 1])))
print(caught(lambda: "a".join([None])), caught(lambda: ",".join(1)))

# `split` with no separator means runs of whitespace, with whatever is at
# either end thrown away. With one it keeps every empty piece it makes.
print("a b  c".split(), " a ".split(), "".split(), "a\f b".split())
print("a b  c".split(" "), "".split(","), "a\n\nb".split("\n"))
print("aaa".split("a"), "aXXb".split("XX"), "XXaXX".split("XX"))
print("a,b,c".split(",", 1), "aaa".split("a", 1), "a b".split(" ", 0))
print("a,b".split(sep=","), "a,b".split(maxsplit=0), "a,b,c".split(",", -1))

# `rsplit` counts its splits from the other end and hands the pieces back in
# the order they appear anyway.
print("a,b,c".rsplit(",", 1), "aaa".rsplit("a", 1), "aaa".rsplit("a"))
print("a b c".rsplit(), "a b c".rsplit(maxsplit=1), " a b ".rsplit(None, 1))
print("abc".split(None, 1), "abc".rsplit(sep=None, maxsplit=1), "a  b".rsplit(None, 1))

# `strip` takes a set of code points off both ends and not a prefix, so the
# argument is not a string to remove but the characters to keep removing.
print(repr("  a b ".strip()), "xxaxx".strip("x"), "abcba".strip("ab"))
print("abc".lstrip("ab"), "abc".rstrip("cb"), "abc".strip(None))
print(repr("abc".strip("")), repr("abc".lstrip("")), repr("  ".strip()))

# `partition` is always three pieces, and on a miss `rpartition` puts the whole
# string last where `partition` puts it first.
print("a=b=c".partition("="), "a=b=c".rpartition("="))
print("abc".partition("z"), "abc".rpartition("z"))
print("abc".partition("bc"), "".partition("a"))

# `replace` with an empty old matches in front of every code point and once
# more at the end, and a negative count means no limit.
print("aaa".replace("a", "b"), "aaa".replace("a", "b", 2), "aaa".replace("aa", "b"))
print("abc".replace("", "-"), "abc".replace("", "-", 2), repr("".replace("", "x")))
print("abc".replace("z", "y"), "abc".replace("a", "b", -1), "abc".replace("a", "b", 0))
print("abc".replace("a", "b", count=1))

# `splitlines` breaks on eleven things and not just on a newline, counts a
# carriage return and newline together as one, and never ends with an empty
# piece.
print("a\nb\n".splitlines(), "a\r\nb".splitlines(), "a\r\n\nb".splitlines())
print("a\rb".splitlines(), "a\x0bb".splitlines(), "a\x1cb".splitlines())
print("a\x85b".splitlines(), "".splitlines(), "\n".splitlines(True))
print("a\nb".splitlines(True), "a\nb".splitlines(keepends=True), "a\nb".splitlines(0))

# `removeprefix` and `removesuffix` take the whole thing off or nothing at all.
print("abc".removeprefix("ab"), "abc".removeprefix("z"), "abc".removesuffix("bc"))
print("abc".removesuffix("z"), repr("abc".removeprefix("abc")), "abc".removesuffix(""))

# Code points and not bytes. The emoji is one of the former and four of the
# latter.
print(len("\U0001f600ab"), "\U0001f600ab".find("a"), "\U0001f600ab".split("a"))
print("abc".replace("b", "\U0001f600"), "ab".join(["\U0001f600"]))

# The wording, which is not uniform and which a program can read. `find` names
# its type for a keyword and not for a count, and the two ways of getting the
# bounds wrong say different things.
print(caught(lambda: "abc".find(1)), caught(lambda: "abc".find()))
print(caught(lambda: "abc".find("a", 0, 1, 2)), caught(lambda: "abc".find("a", x=1)))
print(caught(lambda: "abc".find("a", "b")), caught(lambda: "abc".find("b", 0, "c")))
print(caught(lambda: "abc".count(1)), caught(lambda: "abc".count()))
print(caught(lambda: "abc".count("a", 0, 1, 2)), caught(lambda: "abc".count("b", 1.0)))
print(caught(lambda: "abc".startswith(1)), caught(lambda: "abc".startswith(["a"])))
print(caught(lambda: "abc".startswith()), caught(lambda: "abc".endswith(1)))
print(caught(lambda: "abc".startswith("a", 0, 1, 2)), caught(lambda: "abc".startswith("a", x=1)))
print(caught(lambda: "abc".startswith("a", 1.0)), caught(lambda: "abc".index("a", 1, "x")))
print(caught(lambda: ",".join()), caught(lambda: ",".join(["a"], ["b"])))
print(caught(lambda: "abc".split("")), caught(lambda: "abc".split(1)))
print(caught(lambda: "abc".split(",", "x")), caught(lambda: "abc".split(",", None)))
print(caught(lambda: "abc".split(x=1)), caught(lambda: "abc".rsplit("")))
print(caught(lambda: "abc".rsplit(1)), caught(lambda: "abc".split(",", sep=",")))
print(caught(lambda: "abc".strip(1)), caught(lambda: "abc".lstrip(1)))
print(caught(lambda: "abc".rstrip(1)), caught(lambda: "abc".strip("a", "b")))
print(caught(lambda: "abc".strip(chars="a")), caught(lambda: "abc".strip(None, None)))
print(caught(lambda: "abc".partition("")), caught(lambda: "abc".partition(1)))
print(caught(lambda: "abc".partition()), caught(lambda: "abc".partition("a", "b")))
print(caught(lambda: "abc".rpartition(1)), caught(lambda: "abc".replace(1, "a")))
print(caught(lambda: "abc".replace("a", 1)), caught(lambda: "abc".replace("a")))
print(caught(lambda: "abc".replace()), caught(lambda: "abc".replace("a", "b", 1, 2)))
print(caught(lambda: "abc".replace("a", "b", "x")), caught(lambda: "abc".replace("a", "b", None)))
print(caught(lambda: "abc".splitlines(1, 2)), caught(lambda: "abc".splitlines(x=1)))
print(caught(lambda: "abc".removeprefix(1)), caught(lambda: "abc".removesuffix(1)))
print(caught(lambda: "abc".removeprefix()), caught(lambda: "abc".removeprefix("a", "b")))
print(caught(lambda: "abc".removeprefix(x=1)))

# `splitlines` takes the truth of its argument rather than a number, so a
# string counts as asking to keep the ends.
print("a\nb".splitlines("x"), "a\nb".splitlines(2), "a\nb".splitlines(None))

# A name a string has not got is an `AttributeError`. A name it has that a
# runtime has not written yet is a different answer again, but that one cannot
# be checked here because CPython just does it, so it lives in the runtime's
# own tests.
print(caught(lambda: "abc".nope))


# The methods are values, so one can be held and called later, and two lookups
# of the same one are equal without being the same object.
found = "a,b,c".split
print(found(","), found is found, "abc".find == "abc".find)
print("abc".find == "abc".count, "abc".find == "abd".find)
