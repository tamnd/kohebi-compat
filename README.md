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

## Two commands

`kohebi-compat run` is the end goal and `kohebi-compat tokens` is what is useful today.

Running whole programs only says something once there is a runtime to run them. There will not be one for a while, and waiting until then means finding out about a frontend bug months after writing it. So the frontend gets compared a stage at a time, against the piece of CPython that does the same job, starting with the lexer.

```console
$ pip install -e '.[dev]'
$ kohebi-compat run suites
$ kohebi-compat run suites --against pypy --against graalpy
$ kohebi-compat run suites --out results/local
```

```console
$ kohebi-compat tokens --kohebi ../kohebi/target/release/kohebi
$ kohebi-compat tokens corpus/local --kohebi ../kohebi/target/release/kohebi
```

Each alternative runtime is compared against the CPython version it targets, not against current stable. PyPy 7.3.23 implements Python 3.11, so running it against a 3.14 oracle mostly measures three releases of error message rewording and says almost nothing about PyPy. `--oracle-python` names the oracle by path for exactly that reason, and because leaving it to `PATH` is how a suite ends up quietly comparing a runtime against itself.

The exit code separates two things that look alike. A disagreement exits 1, and so does a run that could not happen at all, meaning the oracle itself failed, a case timed out, or the interpreter being measured is not installed. `--tolerate-mismatch` forgives the first and never the second, which is what the PyPy and GraalPy jobs use: their disagreements with CPython are the measurement, but a job that installed nothing and measured nothing has to stay red.

Comparison is strict by default. Traceback file names, line numbers, and caret positions are compared, because getting them right is a real requirement and is the first thing users notice. `--lenient` compares only the final exception line, and exists for triage rather than for reporting.

## Comparing token streams

CPython ships a tokenizer written in Python. `tokenize.generate_tokens` will run over any file, which turns every `.py` file on the machine into a test case nobody had to write, and the default corpus for `kohebi-compat tokens` is the standard library of the oracle interpreter. Roughly 1900 files of real Python written by many hands over thirty years. On its first run it found three bugs in a lexer that already passed 62 hand written tests: an extra `DEDENT` for every block open at the end of a file, a missing `NL` on a file ending in a comment with no newline, and positions on the last line of a file that does not end with a newline.

There are two oracles here, and the difference matters. For a file that tokenizes, `tokenize` is the oracle and the token streams have to agree element for element. For a file that does not, `compile` is the oracle, because the error messages kohebi is reproducing are the compiler's. The two do not always agree with each other: `tokenize` returns a `NAME` for `€ = 2` and the compiler says `invalid character '€' (U+20AC)`, and the compiler is what a user sees.

Every file lands in one of these, and only some of them are failures:

| Outcome | Meaning | Fails the build |
| --- | --- | --- |
| `match` | Same tokens, or the same refusal in the same words | |
| `mismatch` | Tokenized differently | yes |
| `false-reject` | We refused a file CPython accepts | yes |
| `false-accept` | We accepted a file CPython refuses | yes |
| `wrong-message` | Both refused it, we said something else | yes |
| `unsupported` | kohebi said so itself, so it is a gap and not a wrong answer | |
| `excluded` | Named in `corpus/exclusions.txt`, with a reason | |
| `unreadable` | Not valid UTF-8, which real corpora contain on purpose | |

A wrong answer always fails. A gap kohebi admits to does not, because "f-strings are not implemented yet" would otherwise keep the build red for weeks and teach everyone to ignore it. It still counts against the agreement percentage, which is the number that says how much of Python works, and `--min-agreement` puts a floor under that number when there is one worth defending.

`corpus/local/` is the other half of the corpus. Real code is written by people who use four spaces, avoid tabs, and do not put a form feed in the middle of a class body, so a corpus of real code exercises the easy half of a tokenizer very thoroughly and the hard half not at all. Those files are small, deliberate, and all of them have to match.

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

1. **CPython's own test suite.** The single most valuable test asset for this project, and it is free. Every exclusion gets enumerated with a reason in a checked-in file. An exclusion reading "we do not support this yet" is fine; an exclusion with no reason is how a compatibility claim rots. `corpus/exclusions.txt` already works this way for the tokenizer comparison, and refuses to load a rule that does not say why.
2. **Package test suites.** Of the top 1000 PyPI packages by download, how many install, import, and pass their own tests. This is the only compatibility metric that predicts whether someone's project will work.
3. **Generated programs.** Grammar-based and mutation-based fuzzing against the oracle, biased toward what breaks runtimes rather than uniformly random.

## What gets published

Three numbers, in the same shape GraalPy publishes theirs so the comparison is direct:

- Percentage of CPython's test suite passing, with exclusions enumerated
- Percentage of the top N PyPI packages that install and import
- Percentage of those packages whose own tests pass

Published as markdown in `results/`, updated by CI, including when the numbers are bad. The raw JSON stays out of the repository and is uploaded as a build artifact instead, because a diff of a timestamped result file says nothing and buries the summary that does. Every project in this space that has been vague about compatibility has lost user trust once people found out for themselves.

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
