"""C3 linearisation and metaclass __call__ ordering."""


class Meta(type):
    def __call__(cls, *args, **kwargs):
        print("meta call", cls.__name__)
        return super().__call__(*args, **kwargs)


class A(metaclass=Meta):
    def who(self):
        return "A"


class B(A):
    pass


class C(A):
    def who(self):
        return "C"


class D(B, C):
    pass


print([c.__name__ for c in D.__mro__])
print(D().who())

try:
    class Bad(D, B):
        pass
except TypeError as exc:
    print("TypeError:", "Cannot create a consistent method resolution" in str(exc))
