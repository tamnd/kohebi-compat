"""`kohebi-compat` command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report
from .normalize import LENIENT, STRICT
from .runner import (
    CPYTHON,
    GRAALPY,
    KOHEBI_BUILD,
    KOHEBI_RUN,
    PYPY,
    Outcome,
    collect,
    compare,
)

_INTERPRETERS = {i.name: i for i in (CPYTHON, KOHEBI_RUN, KOHEBI_BUILD, PYPY, GRAALPY)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kohebi-compat",
        description="Run the differential compatibility suite against CPython.",
    )
    parser.add_argument(
        "suite",
        type=Path,
        nargs="?",
        default=Path("suites"),
        help="Directory of .py cases to run (default: suites).",
    )
    parser.add_argument(
        "--against",
        action="append",
        default=None,
        metavar="NAME",
        choices=sorted(_INTERPRETERS),
        help="Interpreter to compare against the oracle. Repeatable.",
    )
    parser.add_argument("--oracle", default="cpython", choices=sorted(_INTERPRETERS))
    parser.add_argument("--timeout", type=float, default=60.0, metavar="SECONDS")
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Compare only the final exception line, not full traceback text.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="DIR",
        help="Write summary.json and report.md here.",
    )
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args(argv)

    if not args.suite.is_dir():
        parser.error(f"{args.suite} is not a directory")

    against = [_INTERPRETERS[n] for n in (args.against or ["kohebi-run", "kohebi-build"])]
    oracle = _INTERPRETERS[args.oracle]
    how = LENIENT if args.lenient else STRICT

    cases = collect(args.suite)
    if not cases:
        print(f"No cases found under {args.suite}.", file=sys.stderr)
        return 1

    print(f"oracle: {oracle.name} ({oracle.version()})", file=sys.stderr)
    for i in against:
        print(f"  vs {i.name}: {i.version()}", file=sys.stderr)

    results = []
    for case in cases:
        result = compare(case, oracle=oracle, against=against, how=how, timeout_s=args.timeout)
        results.append(result)
        if not args.quiet:
            mark = {
                Outcome.MATCH: "ok  ",
                Outcome.MISMATCH: "FAIL",
                Outcome.TIMEOUT: "time",
                Outcome.NOT_INSTALLED: "skip",
                Outcome.ORACLE_FAILED: "??  ",
                Outcome.SKIPPED: "skip",
            }[result.outcome]
            detail = f"  ({', '.join(result.disagreed)})" if result.disagreed else ""
            print(f"{mark} {case}{detail}", file=sys.stderr)

    summary = report.summarise(results)
    print(report.to_markdown(summary, results))

    if args.out:
        report.write(summary, results, args.out)
        print(f"wrote {args.out}/summary.json", file=sys.stderr)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
