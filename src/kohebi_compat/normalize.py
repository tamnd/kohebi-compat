"""Normalisation of interpreter output before comparison.

Two interpreters can be behaving identically and still produce different bytes.
Object reprs carry heap addresses. Tracebacks carry absolute paths. Those
differences are noise, and if we do not remove them every single test fails and
the suite tells us nothing.

The risk runs the other way too. Every normalisation here is a compatibility
difference we have chosen to stop noticing, so each one needs a reason, and the
set should stay small enough to read in one sitting. Anything that hides a real
semantic difference does not belong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# `<object at 0x7f3c8a0b1e50>` -> `<object at 0xADDR>`.
# Heap addresses are never part of a compatibility claim.
_ADDRESS = re.compile(rb"0x[0-9a-fA-F]{4,16}")

# Absolute paths in tracebacks. The suite runs from a temporary directory whose
# name differs between runs, so the path is noise but the basename is not.
_FILE_LINE = re.compile(rb'File "([^"]*)"')

# CPython appends a hint to some errors that other runtimes phrase differently.
# Deliberately NOT normalised: error message text is a compatibility
# requirement and users notice it. See docs/spec/07-compatibility.md.


@dataclass(frozen=True, slots=True)
class Normalisation:
    """Which differences to ignore. Every field defaults to strict."""

    addresses: bool = True
    """Replace heap addresses with a placeholder. Effectively always wanted."""

    paths: bool = True
    """Reduce paths in tracebacks to their basename."""

    traceback_detail: bool = False
    """Drop everything but the final exception line.

    Off by default and it should stay off. Getting file names, line numbers, and
    caret positions right is a real requirement and it is the first thing users
    notice.
    """

    trailing_whitespace: bool = True


STRICT = Normalisation()
LENIENT = Normalisation(traceback_detail=True)


def normalise(data: bytes, how: Normalisation = STRICT) -> bytes:
    """Apply `how` to one stream of captured output."""
    if how.addresses:
        data = _ADDRESS.sub(b"0xADDR", data)
    if how.paths:
        data = _FILE_LINE.sub(_basename_only, data)
    if how.traceback_detail:
        data = _final_exception_line(data)
    if how.trailing_whitespace:
        data = b"\n".join(line.rstrip() for line in data.split(b"\n"))
    return data


def _basename_only(match: re.Match[bytes]) -> bytes:
    path = match.group(1)
    base = path.rsplit(b"/", 1)[-1].rsplit(b"\\", 1)[-1]
    return b'File "' + base + b'"'


def _final_exception_line(data: bytes) -> bytes:
    """Keep the last non-indented line, which is the exception itself."""
    lines = data.split(b"\n")
    for line in reversed(lines):
        stripped = line.strip()
        if stripped and not line.startswith((b" ", b"\t")):
            return stripped
    return data.strip()
