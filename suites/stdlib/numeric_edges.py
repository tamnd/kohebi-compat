"""Integer and float behaviour that a fast path is tempted to get wrong."""

import math

print(2**64)
print((2**63 - 1) + 1)
print(-7 // 2, -7 % 2, divmod(-7, 2))
print(7 // -2, 7 % -2, divmod(7, -2))
print(int("0x1f", 16), int("1_000"))
print(0.1 + 0.2, 0.1 + 0.2 == 0.3)
print(math.isclose(0.1 + 0.2, 0.3))
print(float("inf") - float("inf"))
print(round(2.5), round(3.5), round(-2.5))
print(hash(1) == hash(1.0) == hash(True))
print(repr(1e16), repr(1e17), repr(-0.0))
print((10**30) // 7, (10**30) % 7)
