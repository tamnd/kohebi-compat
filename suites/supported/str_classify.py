"""The twelve methods that ask a string what it is made of.

Every name starts with `is` and there are only eleven questions between them,
because `isalnum` is the union of four of the others rather than a property of
its own. The names do not tell you which of them nest and which of them
overlap, so the ones that get confused for each other are printed side by side.

Three of them have a rule that reads the whole string rather than each
character in turn, and those are the ones a plausible implementation gets
wrong: `islower` and `isupper` want one character that leans their way and none
that leans the other, and `istitle` wants a shape.

Only characters that have been in Unicode for a long time are used here. The
oracles run from 3.11 to 3.15 and those carry three different versions of the
character database between them, so a recently assigned code point would be
comparing the release rather than the runtime.
"""


def caught(thunk):
    """What a call gave back, or what it was refused with."""
    try:
        return repr(thunk())
    except TypeError as e:
        return "TypeError: " + str(e)


# The three number questions nest. An Arabic-Indic three is all three of them,
# a superscript three is a digit and a number and not a decimal because it is
# not a position in a numeral, and a half is only a number.
print("٣".isdecimal(), "٣".isdigit(), "٣".isnumeric())
print("³".isdecimal(), "³".isdigit(), "³".isnumeric())
print("½".isdecimal(), "½".isdigit(), "½".isnumeric())
print("7".isdecimal(), "7".isdigit(), "7".isnumeric(), "a".isnumeric())

# `isalpha` and the number ones do not cover each other and do not exhaust
# `isalnum`. A CJK ideograph is a letter and a number both. A roman numeral is
# a number and not a letter. An Arabic-Indic digit is neither a letter nor
# anything `isalnum` would miss.
print("一".isalpha(), "一".isnumeric(), "一".isalnum())
print("ⅰ".isalpha(), "ⅰ".isnumeric(), "ⅰ".isalnum())
print("٣".isalpha(), "٣".isalnum(), "a1".isalnum(), "a-1".isalnum())

# `islower` is not every character being lowercase. It is one at least that is
# and none that is not, so punctuation and digits are neither for nor against.
print("abc!".islower(), "abc".islower(), "aBc".islower(), "!".islower())
print("ABC!".isupper(), "AbC".isupper(), "1".isupper(), "".isupper())
# A titlecase character leans neither way and counts against both of them, so
# the digraph below is not lower and not upper either.
print("ǅ".islower(), "ǅ".isupper(), "ǅ".istitle())
# Cased is not the same as alphabetic in either direction. Hiragana is a letter
# and has no case, and a roman numeral has a case and is not a letter.
print("あ".islower(), "あ".isupper(), "ⅰ".islower(), "Ⅰ".isupper())

# `istitle` wants every word started exactly once by an uppercase or titlecase
# character and carried on in lowercase, and it wants at least one word.
print("Hello World".istitle(), "Hello world".istitle(), "HELLO".istitle())
print("They're".istitle(), "They'Re".istitle(), "A".istitle())
# What ends a word is a character that has no case, so a digit inside one
# starts a new word and breaks the shape.
print("Ab1Cd".istitle(), "Ab1cd".istitle(), "123".istitle(), " ".istitle())

# `isspace` is Python's list and not Unicode's. The four file and group
# separators count here and do not count as whitespace anywhere else.
print("\x1c".isspace(), "\x1f".isspace(), "\xa0".isspace(), "\x0b".isspace())
print(" \t\n".isspace(), " a".isspace(), "\x00".isspace())

# `isidentifier` knows nothing about keywords, so the caller is the one who has
# to care, and it does not normalise either, so this ligature is an identifier
# here and is the name `fi` in a program.
print("if".isidentifier(), "ﬁ".isidentifier(), "_".isidentifier())
print("a1".isidentifier(), "1a".isidentifier(), "a b".isidentifier())
print("あ".isidentifier(), "٣".isidentifier(), "a-b".isidentifier())

# `isascii` and `isprintable` are claims about what a string does not contain
# rather than about what it does.
print("abc".isascii(), "ä".isascii(), "a b".isascii(), "\x00".isascii())
print("a b".isprintable(), "a\tb".isprintable(), "\xa0".isprintable())
print("ä".isprintable(), "\x1c".isprintable())

# Ten of the twelve are false for the empty string, because a claim about every
# character is worth nothing when there are none. The two that are claims about
# absence are true for it instead.
print("".isalnum(), "".isalpha(), "".isascii(), "".isdecimal())
print("".isdigit(), "".isidentifier(), "".islower(), "".isnumeric())
print("".isprintable(), "".isspace(), "".istitle(), "".isupper())

# All twelve take no arguments, and all twelve say so the same way.
print(caught(lambda: "a".isalpha(1)), caught(lambda: "a".isdigit(x=1)))
print(caught(lambda: "a".isidentifier(1, 2)), caught(lambda: "a".isspace(None)))
