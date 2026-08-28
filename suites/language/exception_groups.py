"""except* and exception groups, plus notes and chaining."""

try:
    raise ExceptionGroup(
        "several",
        [ValueError("v"), TypeError("t"), ValueError("v2")],
    )
except* ValueError as eg:
    print("values:", [str(e) for e in eg.exceptions])
except* TypeError as eg:
    print("types:", [str(e) for e in eg.exceptions])

try:
    try:
        1 / 0
    except ZeroDivisionError as exc:
        exc.add_note("a note")
        raise RuntimeError("wrapped") from exc
except RuntimeError as exc:
    print(type(exc).__name__, exc)
    print("cause:", type(exc.__cause__).__name__, exc.__cause__.__notes__)
