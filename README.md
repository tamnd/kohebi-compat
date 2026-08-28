# kohebi-compat

CPython compatibility suite for [kohebi](https://github.com/tamnd/kohebi), a Python runtime written in Rust.

[![Compatibility](https://github.com/tamnd/kohebi-compat/actions/workflows/compat.yml/badge.svg)](https://github.com/tamnd/kohebi-compat/actions/workflows/compat.yml)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

> [!NOTE]
> kohebi is not implemented yet, so the suite currently runs against CPython, PyPy, and GraalPy only. It is built first on purpose: testing infrastructure written after the runtime is testing infrastructure shaped around the bugs the runtime already has.

## The idea

kohebi's correctness claim is "matches CPython". That gives an executable oracle: for any program, CPython's behaviour is the right answer, and disagreement is a bug by definition.

So the suite runs the same program under several interpreters and requires them to agree on stdout, stderr, and exit code:

```
CPython 3.14        the oracle
kohebi run          JIT mode
kohebi build        AOT mode
```

Two-way disagreements are informative in themselves. CPython and `kohebi run` agreeing while `kohebi build` differs means the AOT compiler is wrong. Both kohebi modes agreeing against CPython means the shared frontend is wrong. That distinction saves a lot of debugging, and it is the mechanism that enforces the claim that the two modes do not drift apart.

## Usage

```console
$ pip install -e '.[dev]'
$ kohebi-compat suites
$ kohebi-compat suites --against pypy --against graalpy
$ kohebi-compat suites --out results/local
```

Each alternative runtime is compared against the CPython version it targets, not against current stable. PyPy 7.3.23 implements Python 3.11, so running it against a 3.14 oracle mostly measures three releases of error message rewording and says almost nothing about PyPy. `--oracle-python` names the oracle by path for exactly that reason, and because leaving it to `PATH` is how a suite ends up quietly comparing a runtime against itself.

The exit code separates two things that look alike. A disagreement exits 1, and so does a run that could not happen at all, meaning the oracle itself failed, a case timed out, or the interpreter being measured is not installed. `--tolerate-mismatch` forgives the first and never the second, which is what the PyPy and GraalPy jobs use: their disagreements with CPython are the measurement, but a job that installed nothing and measured nothing has to stay red.

Comparison is strict by default. Traceback file names, line numbers, and caret positions are compared, because getting them right is a real requirement and is the first thing users notice. `--lenient` compares only the final exception line, and exists for triage rather than for reporting.

## What is normalised, and what is not

Two interpreters can behave identically and still produce different bytes. Heap addresses and absolute paths are noise. Every normalisation is a compatibility difference we have chosen to stop noticing, so the list is deliberately short and lives in [`src/kohebi_compat/normalize.py`](src/kohebi_compat/normalize.py).

Notably **not** normalised: error message text. Message wording is a compatibility requirement, and a runtime that gets `TypeError: unsupported operand type(s) for +: 'int' and 'str'` subtly wrong will break doctests, test suites, and user expectations.

## Suites

| Directory | What it covers |
| --- | --- |
| `suites/language/` | Descriptors, MRO and metaclasses, generators and `finally`, exception groups, frame introspection and `sys.settrace`, `exec`/`eval`/monkeypatching |
| `suites/stdlib/` | Integer and float edges, string and Unicode behaviour across scripts |

These are the places runtimes reliably diverge. They are chosen to be hostile to exactly the optimisations kohebi intends to make: caching attribute lookups, assuming classes do not change, and assuming frames are not observable.

The suite grows in three further directions, none of which exist yet:

1. **CPython's own test suite.** The single most valuable test asset for this project, and it is free. Every exclusion gets enumerated with a reason in a checked-in file. An exclusion reading "we do not support this yet" is fine; an exclusion with no reason is how a compatibility claim rots.
2. **Package test suites.** Of the top 1000 PyPI packages by download, how many install, import, and pass their own tests. This is the only compatibility metric that predicts whether someone's project will work.
3. **Generated programs.** Grammar-based and mutation-based fuzzing against the oracle, biased toward what breaks runtimes rather than uniformly random.

## What gets published

Three numbers, in the same shape GraalPy publishes theirs so the comparison is direct:

- Percentage of CPython's test suite passing, with exclusions enumerated
- Percentage of the top N PyPI packages that install and import
- Percentage of those packages whose own tests pass

Published in `results/`, updated by CI, including when the numbers are bad. Every project in this space that has been vague about compatibility has lost user trust once people found out for themselves.

## Reference points

Measured on the same suite, so the bar is visible:

| Runtime | Version tracked |
| --- | --- |
| CPython | 3.14 (stable), 3.15 (rc) |
| PyPy | 7.3.23, targeting Python 3.11 |
| GraalPy | 25.2, targeting Python 3.12 |

GraalPy is the compatibility standard to beat and the honest indication of how hard this is: after roughly a decade with Oracle behind it, some recent version of 93% of the 600 most-depended-on PyPI packages installs, and more than 65% of those packages' own tests pass.

## Related

| Repository | Purpose |
| --- | --- |
| [tamnd/kohebi](https://github.com/tamnd/kohebi) | The runtime |
| [tamnd/kohebi-bench](https://github.com/tamnd/kohebi-bench) | Benchmarks against CPython, PyPy, GraalPy |

## License

MIT or Apache-2.0, at your option.
