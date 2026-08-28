"""CPython compatibility suite for the kohebi Python runtime.

See https://github.com/tamnd/kohebi for the runtime this measures.
"""

from .normalize import LENIENT, STRICT, Normalisation, normalise
from .runner import (
    CPYTHON,
    GRAALPY,
    KOHEBI_BUILD,
    KOHEBI_RUN,
    PYPY,
    Execution,
    Interpreter,
    Outcome,
    Result,
    collect,
    compare,
    execute,
)

__version__ = "0.0.0"

__all__ = [
    "CPYTHON",
    "GRAALPY",
    "KOHEBI_BUILD",
    "KOHEBI_RUN",
    "LENIENT",
    "PYPY",
    "STRICT",
    "Execution",
    "Interpreter",
    "Normalisation",
    "Outcome",
    "Result",
    "collect",
    "compare",
    "execute",
    "normalise",
]
