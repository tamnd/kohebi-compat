"""`kohebi-compat` command line entry point.

Three subcommands, because a runtime that cannot run a program yet still has
parts worth checking:

    kohebi-compat run      whole programs, compared by what they print
    kohebi-compat tokens   token streams, compared against CPython's tokenizer
    kohebi-compat trees    syntax trees, compared against CPython's `ast.dump`

`run` is the end goal. The other two are what tell us today whether the
frontend is right, over a corpus far larger than anything we would write by
hand. They take the same arguments and differ only in which stage they ask
both sides about.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

from . import report, tokens, trees
from .corpus import Exclusions, FileOutcome, FileResult, default_corpus, find_kohebi
from .normalize import LENIENT, STRICT
from .runner import (
    CPYTHON,
    GRAALPY,
    KOHEBI_BUILD,
    KOHEBI_RUN,
    PYPY,
    Interpreter,
    Outcome,
    collect,
    compare,
)

Differential = Callable[..., Iterator[FileResult]]
"""A corpus comparison: paths in, one result per path out."""

_INTERPRETERS = {i.name: i for i in (CPYTHON, KOHEBI_RUN, KOHEBI_BUILD, PYPY, GRAALPY)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kohebi-compat",
        description="Compare kohebi against CPython.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_run(sub.add_parser("run", help="Run whole programs and compare their output."))
    _add_corpus(
        sub.add_parser("tokens", help="Compare token streams against CPython."),
        stage="tokenize",
        stem="tokens",
    )
    _add_corpus(
        sub.add_parser("trees", help="Compare syntax trees against CPython."),
        stage="parse",
        stem="trees",
    )
    args = parser.parse_args(argv)
    if args.command == "tokens":
        return _corpus(
            args,
            parser,
            differential=tokens.run,
            title="Tokenizer agreement",
            stem="tokens",
            noun="tokenized",
        )
    if args.command == "trees":
        return _corpus(
            args,
            parser,
            differential=trees.run,
            title="Parser agreement",
            stem="trees",
            noun="parsed",
        )
    return _run(args, parser)


def _add_run(parser: argparse.ArgumentParser) -> None:
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
    parser.add_argument(
        "--oracle-python",
        default=None,
        metavar="PATH",
        help=(
            "Exact interpreter to use as the oracle, overriding the command "
            "looked up on PATH. Use this when comparing a runtime that targets "
            "an older Python: PyPy 7.3.23 implements 3.11, and comparing it "
            "against a 3.14 oracle mostly measures the three versions in "
            "between rather than anything about PyPy."
        ),
    )
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
    parser.add_argument(
        "--tolerate-mismatch",
        action="store_true",
        help=(
            "Exit 0 when the only failures are mismatches. This is for "
            "measuring a runtime that is not kohebi, where disagreement with "
            "CPython is the result rather than a regression. A run that could "
            "not happen at all, meaning a failed oracle, a timeout or a "
            "missing interpreter, still exits non-zero."
        ),
    )
    parser.add_argument("--quiet", "-q", action="store_true")


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.suite.is_dir():
        parser.error(f"{args.suite} is not a directory")

    against = [_INTERPRETERS[n] for n in (args.against or ["kohebi-run", "kohebi-build"])]
    oracle = _INTERPRETERS[args.oracle]
    if args.oracle_python:
        oracle = Interpreter(oracle.name, (args.oracle_python,))
        if not oracle.available():
            parser.error(f"--oracle-python {args.oracle_python} is not executable")
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

    # A suite that could not run is a different failure from a suite that ran
    # and found disagreements, and only the second one is ever tolerable.
    broken = [
        r
        for r in results
        if r.outcome in (Outcome.ORACLE_FAILED, Outcome.TIMEOUT, Outcome.NOT_INSTALLED)
    ]
    if broken:
        print(f"{len(broken)} case(s) could not be run: {broken[0].note}", file=sys.stderr)
        return 1
    if args.tolerate_mismatch:
        return 0
    return 0 if all(r.passed for r in results) else 1


def _add_corpus(parser: argparse.ArgumentParser, *, stage: str, stem: str) -> None:
    """Arguments shared by every differential that walks a corpus of files.

    `tokens` and `trees` ask about different stages and are otherwise the same
    command, so they get the same flags rather than two sets that drift apart.
    """
    parser.add_argument(
        "corpus",
        type=Path,
        nargs="*",
        default=None,
        help=(
            f"Directories or files to {stage}. Defaults to the standard "
            "library of the oracle interpreter, which is a few thousand files "
            "of real Python that are already on the machine."
        ),
    )
    parser.add_argument(
        "--kohebi",
        default=None,
        metavar="PATH",
        help="The kohebi binary. Defaults to whatever is on PATH.",
    )
    parser.add_argument(
        "--oracle-python",
        default=None,
        metavar="PATH",
        help="Interpreter whose standard library becomes the default corpus.",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("corpus/exclusions.txt"),
        metavar="FILE",
        help="Rules for files not to compare, each with a reason.",
    )
    parser.add_argument("--jobs", "-j", type=int, default=8, metavar="N")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Compare only the first N files. For a quick check.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"Write {stem}.json and {stem}.md here.",
    )
    parser.add_argument(
        "--min-agreement",
        type=float,
        default=None,
        metavar="RATIO",
        help=(
            "Also fail if agreement falls below this, on top of failing on "
            "any wrong answer. Use it to stop coverage sliding backwards "
            "while parts of the language are still unimplemented."
        ),
    )
    parser.add_argument("--quiet", "-q", action="store_true")


def _corpus(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    *,
    differential: Differential,
    title: str,
    stem: str,
    noun: str,
) -> int:
    kohebi = find_kohebi(args.kohebi)
    if kohebi is None:
        parser.error(
            "cannot find the kohebi binary. Build it with `cargo build` in the "
            "kohebi checkout and pass --kohebi target/debug/kohebi."
        )

    roots = args.corpus or [default_corpus(args.oracle_python)]
    paths = _gather(roots)
    if not paths:
        print(f"No .py files under {', '.join(str(r) for r in roots)}.", file=sys.stderr)
        return 1
    if args.limit is not None:
        paths = paths[: args.limit]

    try:
        exclusions = Exclusions.load(args.exclusions)
    except ValueError as exc:
        parser.error(str(exc))

    print(f"corpus: {len(paths)} files from {', '.join(str(r) for r in roots)}", file=sys.stderr)

    results = []
    for result in differential(paths, kohebi=kohebi, exclusions=exclusions, jobs=args.jobs):
        results.append(result)
        if not args.quiet and result.outcome not in (
            FileOutcome.MATCH,
            FileOutcome.EXCLUDED,
            FileOutcome.UNREADABLE,
        ):
            print(f"{result.outcome.value:14} {result.path}: {result.detail}", file=sys.stderr)

    summary = report.summarise_files(results)
    print(report.files_to_markdown(summary, results, title=title))

    if args.out:
        report.write_files(summary, results, args.out, stem=stem, title=title)
        print(f"wrote {args.out}/{stem}.md", file=sys.stderr)

    # Two separate failures. A wrong answer is always a bug and always fails.
    # A gap kohebi admits to is not a bug, it is coverage, and it fails only
    # against a floor someone chose, because otherwise "we do not implement
    # f-strings yet" would keep the build red for weeks and teach everyone to
    # ignore it.
    wrong = [r for r in results if not r.passed]
    if wrong:
        print(f"{len(wrong)} file(s) {noun} differently from CPython", file=sys.stderr)
        return 1
    if args.min_agreement is not None and summary.agreement < args.min_agreement:
        print(
            f"agreement {summary.agreement:.2%} is below the floor of {args.min_agreement:.2%}",
            file=sys.stderr,
        )
        return 1
    return 0


def _gather(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_dir():
            found.extend(root.rglob("*.py"))
        elif root.exists():
            found.append(root)
    return sorted(set(found))


if __name__ == "__main__":
    raise SystemExit(main())
