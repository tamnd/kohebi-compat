"""`pathlib.Path`, or the part of it that never touches a disk.

A path is text with a grammar, and almost everything a program does with one is
reading that grammar rather than asking the filesystem anything. That half is
what is checked here, because it is the half with the corners in it: which dot
starts an extension, what the parent of a bare name is, what happens to the
piece in front when the piece behind has a root of its own.

Every path printed here goes through `as_posix`, because Windows writes a
separator this file would otherwise have to spell twice. The one thing that
still differs between platforms is `parts`, whose first element is the anchor,
so the cases that print it use relative paths only.

Nothing here reads the filesystem. `resolve` and `exists` depend on where the
suite is run from and on what is on the machine running it, so they are not
comparable output and are left to the runtime's own tests.
"""

from pathlib import Path

# Separators fold, a lone dot goes, and a trailing separator is not a name.
print(Path("a//b").as_posix(), Path("a/b/").as_posix(), Path("./a").as_posix())
print(Path("a/./b").as_posix(), Path("").as_posix(), Path(".").as_posix())

# `..` stays where it was written, because `a/../b` and `b` are different paths
# whenever `a` is a symbolic link and no amount of tidying the text knows that.
print(Path("a/../b").as_posix())

# Several segments join, and one with a root of its own starts again.
print(Path("a", "b", "c").as_posix(), Path("a", "/b").as_posix())
print((Path("a") / "b").as_posix(), ("a" / Path("b")).as_posix())
print((Path("a") / Path("/b")).as_posix(), Path("a").joinpath("b", "c").as_posix())

# The pieces. `parent` walks up and stops rather than going past the top.
p = Path("a/b/c.tar.gz")
print(p.name, p.stem, p.suffix, p.suffixes)
print(p.parent.as_posix(), p.parent.parent.as_posix(), p.parent.parent.parent.as_posix())
print(Path("a").parent.as_posix(), Path(".").parent.as_posix())
print(p.parts, Path("a").parts, Path(".").parts)

# A leading dot is part of the name rather than the start of an extension.
print(repr(Path(".bashrc").suffix), repr(Path(".bashrc").stem), Path(".tar.gz").suffixes)
print(repr(Path("a").suffix), repr(Path("a").stem))

# The last name replaced, and the last extension replaced or taken off.
print(p.with_name("d.txt").as_posix(), p.with_suffix(".txt").as_posix())
print(p.with_suffix("").as_posix(), Path("a/b").with_suffix(".txt").as_posix())

# Two paths are equal when they come out the same, which is not the same as
# naming the same file.
print(Path("a") == Path("./a"), Path("a/../b") == Path("b"), Path("a") == "a")

# A relative path is relative on every platform. Whether `/a` is absolute is
# not: Windows wants a drive as well, so that one is not asked here.
print(Path("a").is_absolute(), Path("a/b").is_absolute())

# The mistakes, and what each of them is called.
try:
    Path(1)
except TypeError as e:
    print("TypeError:", e)
try:
    Path("a") / 1
except TypeError as e:
    print("TypeError:", e)
try:
    Path("a").with_suffix("txt")
except ValueError as e:
    print("ValueError:", e)
try:
    Path("a").nosuchthing
except AttributeError as e:
    print("AttributeError:", e)
