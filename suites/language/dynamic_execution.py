"""exec, eval, and compile against a live namespace."""

namespace = {"seed": 10}
exec("doubled = seed * 2", namespace)
print(namespace["doubled"])

code = compile("[x * seed for x in range(3)]", "<generated>", "eval")
print(eval(code, namespace))


class Dynamic:
    pass


for name in ("alpha", "beta"):
    setattr(Dynamic, name, property(lambda self, n=name: f"value-{n}"))

d = Dynamic()
print(d.alpha, d.beta)
print(hasattr(d, "gamma"))

# Monkeypatching a class after instances exist must invalidate any cached lookup.
inst = Dynamic()
print(inst.alpha)
Dynamic.alpha = property(lambda self: "patched")
print(inst.alpha)
