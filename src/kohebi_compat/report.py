"""Turning results into the three numbers we publish.

Per docs/spec/07-compatibility.md, kohebi publishes compatibility in the same
shape GraalPy does, so the comparison is direct: what fraction of CPython's own
test suite passes, what fraction of the top PyPI packages install and import,
and what fraction of those packages' own tests pass.

The rule that makes those numbers worth anything: every exclusion is
enumerated with a reason. An exclusion reading "we do not support this yet" is
fine. An exclusion with no reason is how a compatibility claim rots.
"""

from __future__ import annotations

import json
import platform
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .runner import Outcome, Result


@dataclass(slots=True)
class Summary:
    total: int
    by_outcome: dict[str, int]
    pass_rate: float
    disagreements: dict[str, int]
    generated_at: str
    host: dict[str, str]

    def to_json(self) -> str:
        # asdict rather than __dict__: this is a slots dataclass, so there is
        # no instance __dict__ to read.
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def summarise(results: list[Result]) -> Summary:
    outcomes = Counter(r.outcome.value for r in results)
    disagreements: Counter[str] = Counter()
    for r in results:
        disagreements.update(r.disagreed)

    considered = [r for r in results if r.outcome is not Outcome.SKIPPED]
    passed = sum(1 for r in considered if r.passed)

    return Summary(
        total=len(results),
        by_outcome=dict(sorted(outcomes.items())),
        pass_rate=round(passed / len(considered), 4) if considered else 0.0,
        disagreements=dict(sorted(disagreements.items())),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        host={
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
        },
    )


def to_markdown(summary: Summary, results: list[Result]) -> str:
    lines = [
        "# Compatibility report",
        "",
        f"Generated {summary.generated_at} on {summary.host['platform']}.",
        "",
        f"**Pass rate: {summary.pass_rate:.1%}** over {summary.total} cases.",
        "",
        "| Outcome | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {k} | {v} |" for k, v in summary.by_outcome.items())

    if summary.disagreements:
        lines += [
            "",
            "## Which configuration disagreed",
            "",
            "| Configuration | Disagreements |",
            "| --- | ---: |",
        ]
        lines.extend(f"| {k} | {v} |" for k, v in summary.disagreements.items())

    failures = [r for r in results if r.outcome is Outcome.MISMATCH]
    if failures:
        lines += ["", "## Mismatches", "", "| Case | Disagreed |", "| --- | --- |"]
        lines.extend(f"| `{r.case}` | {', '.join(r.disagreed)} |" for r in failures[:200])
        if len(failures) > 200:
            lines.append(f"| ... | {len(failures) - 200} more |")

    return "\n".join(lines) + "\n"


def write(summary: Summary, results: list[Result], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(summary.to_json())
    (out / "report.md").write_text(to_markdown(summary, results))
