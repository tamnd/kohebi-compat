"""`int` and `float` reading a string.

This is a wider grammar than a literal in source and that is the whole reason
the case exists. A literal cannot have whitespace around it, cannot have a
sign, cannot be given a base, and cannot be written in Arabic-Indic digits, and
`int` of a string can do all four. Everything below was checked against a
running CPython rather than reasoned about, including which complaint comes out
of which mistake and in which order.

`bytes` is here as an argument rather than as a constructor of its own, since
`int(b'12')` is 12 and the digits in a `bytes` are bytes rather than text.
"""

print(int(), int(0), int(7), int(-5), int(True), int(False))
print(int("0"), int("12"), int("-12"), int("+12"), int(" 12 "), int("\t12\n"))
print(int("1_0"), int("1_0_0"), int("9" * 25), int("-" + "9" * 25))
print(int(1.9), int(-1.9), int(0.0), int(-0.5), int(1e18))
print(int(b"12"), int(b" 12 "), int(b"1", 2))

# A base, which a literal cannot be given, and the prefixes that go with one.
# A prefix is only a prefix when the base agrees with it.
print(int("ff", 16), int("FF", 16), int("0xff", 16), int("0Xff", 16))
print(int("101", 2), int("0b101", 2), int("z", 36), int("Z", 36), int("10", 36))
print(int("0b101", 0), int("0o17", 0), int("0x1f", 0), int("-0x1f", 0))
print(int("1", base=2), int("1", 0), int("1", False))

# An underscore wants a digit on each side, with one exception: a single one
# may follow a base prefix.
print(int("0x_ff", 16), int("0b_1", 0), float("1_0.5"), float("1e1_0"))

# Base 0 is the only one that refuses a leading zero that means nothing.
print(int("00", 0), int("0_0_0", 0), int("0", 0), int("010", 10))

# Decimal digits from any script, worth their decimal value in every base.
print(int("١٢"), int("١٢", 16), int("١٢", 36), int("１f", 16), int("١_٢"))
print(float("١٢"), float("１.５e１"), float("١_٢"))

print(float(), float(0), float(7), float(True), float(-3), float(1.5))
print(float("1.5"), float(".5"), float("5."), float("+.5"), float("-.5"))
print(float("1e5"), float("1E5"), float("1e+5"), float("1e-5"), float(" 1.5 "))
print(float("INF"), float("-Infinity"), float("-iNf"), float("nan"))
print(float(b"1.5"), float(2**62), float("0_1"), float("1.0_1"))


def check(label, work):
    try:
        print(label, "->", work())
    except (TypeError, ValueError, OverflowError) as e:
        print(label, "->", type(e).__name__ + ":", e)


# A string that is not a number quotes the string it was given, whitespace and
# all, and names the base that was asked for even when the base was 0.
check('int("abc")', lambda: int("abc"))
check('int(" abc ")', lambda: int(" abc "))
check('int("1.5")', lambda: int("1.5"))
check('int("")', lambda: int(""))
check('int("  ")', lambda: int("  "))
check('int(b"abc")', lambda: int(b"abc"))
check('int("_1")', lambda: int("_1"))
check('int("1_")', lambda: int("1_"))
check('int("1__0")', lambda: int("1__0"))
check('int("0x__ff", 16)', lambda: int("0x__ff", 16))
check('int("0x", 16)', lambda: int("0x", 16))
check('int("0x1f", 8)', lambda: int("0x1f", 8))
check('int("0_1", 0)', lambda: int("0_1", 0))
check('int("010", 0)', lambda: int("010", 0))
check('int("²")', lambda: int("²"))

# The base is looked at before the value, so a bad base wins over a bad value,
# and a missing value with a base present wins over both.
check('int("1", 1)', lambda: int("1", 1))
check('int("1", 37)', lambda: int("1", 37))
check('int("1", -1)', lambda: int("1", -1))
check('int("1", True)', lambda: int("1", True))
check('int("1", 2.0)', lambda: int("1", 2.0))
check("int(None, 99)", lambda: int(None, 99))
check('int(None, "x")', lambda: int(None, "x"))
check("int(1, 10)", lambda: int(1, 10))
check("int(1.5, 10)", lambda: int(1.5, 10))
check("int(base=16)", lambda: int(base=16))

# Two arities and two different complaints about the same count, which is not
# something anyone would guess.
check('int("1", 2, 3)', lambda: int("1", 2, 3))
check('int("1", 2, base=3)', lambda: int("1", 2, base=3))
check('int(x="1")', lambda: int(x="1"))

check("int(None)", lambda: int(None))
check("int([])", lambda: int([]))
check("int(())", lambda: int(()))
check('int(float("nan"))', lambda: int(float("nan")))
check('int(float("inf"))', lambda: int(float("inf")))
check('int(float("-inf"))', lambda: int(float("-inf")))

# `float` takes one argument and no keyword at all, which is the other shape.
check('float("abc")', lambda: float("abc"))
check('float("")', lambda: float(""))
check('float("+")', lambda: float("+"))
check('float(".")', lambda: float("."))
check('float("1e")', lambda: float("1e"))
check('float("e5")', lambda: float("e5"))
check('float("1.5.5")', lambda: float("1.5.5"))
check('float("0x1f")', lambda: float("0x1f"))
check('float("nan(1)")', lambda: float("nan(1)"))
check('float("infinit")', lambda: float("infinit"))
check('float("1_.5")', lambda: float("1_.5"))
check('float("1.5_")', lambda: float("1.5_"))
check('float("1.5e_1")', lambda: float("1.5e_1"))
check('float(b"abc")', lambda: float(b"abc"))
check("float(None)", lambda: float(None))
check("float([])", lambda: float([]))
check("float(2**1024)", lambda: float(2**1024))
check("float(x=1)", lambda: float(x=1))
check("float(1, 2)", lambda: float(1, 2))
