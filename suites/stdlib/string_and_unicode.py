"""String representation across scripts, plus the identity assumptions."""

samples = ["ascii", "café", "日本語", "🐍 kohebi", "á"]
for s in samples:
    print(repr(s), len(s), len(s.encode()), s.upper(), s[::-1])

print("café".encode("utf-8").decode("utf-8") == "café")
print(sorted(samples, key=len))
print("".join(reversed("日本語")))
print("%s and %r" % ("x", "y"), f"{1/3:.4f}")
print("abc".encode().hex(), bytes.fromhex("616263"))
