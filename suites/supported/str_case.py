"""The six methods that change the case of a string.

`upper`, `lower`, `title`, `capitalize`, `swapcase` and `casefold`. Not one of
them is a mapping of one code point to one code point, and no two of them agree
on what to do with every character, so all six are checked side by side.

The interesting cases are the ones a plausible rule gets wrong. A character
whose uppercase is two characters. A titlecase that is neither the uppercase
nor the lowercase. A word boundary that is not where the letters are. And the
Greek sigma, which is the one letter whose lowercase depends on the rest of the
string rather than on itself.

Nobody can tell the three forms of a digraph apart at a glance, so the comments
say which is which rather than leaving the glyph to speak for itself.
"""


def caught(thunk):
    """What a call gave back, or what it was refused with."""
    try:
        return repr(thunk())
    except TypeError as e:
        return "TypeError: " + str(e)


# `upper` and `lower`, where the length of the answer is not the length of the
# question. The sharp s uppercases to two letters, the ligature to three, and
# the dotted capital I lowercases to a letter and a combining dot.
print(repr("ß".upper()), repr("ﬃ".upper()), repr("ǰ".upper()))
print(repr("İ".lower()), repr("ß".lower()), repr("abc".upper()))
print(repr("".upper()), repr("".lower()), repr("123 !".upper()))

# The final sigma. `Σ` lowercases to `ς` at the end of a word and to
# `σ` everywhere else, so the answer needs the rest of the string.
print("ΑΣ".lower(), "ΑΣΑ".lower(), "Σ".lower())
# The scan reads the input and not the output, which is what this shows: the
# first sigma has a cased character after it and the second has not.
print("ΑΣΣ".lower(), "ΟΔΟΣ ΟΔΟΣ".lower())
# A quote and a full stop are looked past in both directions, so neither of
# them ends a word here and neither of them starts one.
print("ΑΣ'".lower(), "Α'Σ".lower(), "ΑΣ.Α".lower())
print("ΣΑ".lower(), ".Σ".lower(), "ΑΣ ".lower())

# `title` starts a word at a cased character. That is not the same as a letter:
# hiragana is a letter and not cased, and a lowercase roman numeral is cased
# and not a letter, so the two rules disagree in both directions.
print("hello world".title(), "123abc".title(), "they're".title())
print("あa".title(), "ⅰa".title(), "ΑΣ ΒΣ".title())
# The character that starts a word gets the titlecase mapping, and for the
# digraphs that is a third character rather than the uppercase one.
print("ǆǆ".title(), "ǆ".upper(), "Ǆ".title())
print(repr("".title()), "ßß".title(), "a b".title())

# `capitalize` is `title` that stops looking after the first character, and the
# first character gets the titlecase mapping rather than the uppercase one.
print(repr("ǆa".capitalize()), repr("ǆa".upper()), repr("".capitalize()))
print("hELLO".capitalize(), "ßa".capitalize(), "123a".capitalize())
# The tail is lowercased against the original string, so the sigma rule applies
# to it in the usual way.
print("σαΣ".capitalize(), "ΣΣ".capitalize())

# `swapcase` asks per character, and the property it asks about is uppercase or
# lowercase rather than cased, so a titlecase character is neither and nothing
# happens to it.
print("aB".swapcase(), "ß".swapcase(), "ΑΣ".swapcase())
print("ǅ".swapcase(), "ⅰ".swapcase(), "1 a".swapcase())

# `casefold` is for comparing rather than for displaying. It is not `lower`,
# and it wants no final sigma, because the whole point is that `ΑΣ`
# and `Ας` come out the same.
print("ß".casefold(), "ß".lower(), "ﬁ".casefold())
print("ΑΣ".casefold(), "Ας".casefold(), "ΑΣ".lower())
print(repr("İ".casefold()), "Σ".casefold(), repr("".casefold()))

# Code points and not bytes, and a character with no case at all is left alone.
print("\U0001f600a".upper(), "\U0001f600".title(), len("ß".upper()))

# All six take no arguments, and all six say so the same way.
print(caught(lambda: "a".upper(1)), caught(lambda: "a".lower(1, 2)))
print(caught(lambda: "a".title(x=1)), caught(lambda: "a".capitalize(1)))
print(caught(lambda: "a".swapcase(None)), caught(lambda: "a".casefold(x=1)))
