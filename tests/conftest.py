"""Fixtures shared by the corpus differentials.

Both differentials drive a kohebi binary over a pipe, and both need to see what
happens when that binary is wrong. A real kohebi that agrees with CPython
cannot demonstrate a disagreement, so the tests stand in a fake one that prints
whatever they tell it to.
"""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

# It reads source on stdin and prints what the test asked for. Bytes on the way
# in, like the real one, since what encoding they are in is the file's own
# business to say.
_FAKE = """\
import sys
sys.stdin.buffer.read()
out = {out!r}
err = {err!r}
sys.stdout.write(out)
sys.stderr.write(err)
sys.exit({code})
"""


@pytest.fixture
def fake_kohebi(tmp_path: Path):
    def make(*, out: str = "", err: str = "", code: int = 0) -> list[str]:
        script = tmp_path / f"fake_{abs(hash((out, err, code)))}.py"
        script.write_text(_FAKE.format(out=out, err=err, code=code))
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return [sys.executable, str(script)]

    return make
