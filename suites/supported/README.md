# Programs kohebi is expected to match today

Everything else under `suites/` is written to be hostile. Descriptors, metaclasses, `sys.settrace` and generator teardown are the places runtimes diverge, and they are in the repository so that the day kohebi reaches them there is already a test that says what the answer is. None of them runs today, and a directory where every case fails is a directory nobody looks at.

This one is the other half. Every program here uses only what kohebi implements, so every one of them has to produce byte for byte what CPython produces, and a run that does not is a regression rather than a gap. It is the net under the features that have already landed, and it grows by one file per feature as the runtime grows.

```console
$ kohebi-compat run suites/supported --against kohebi-run --min-agreement 100
```

The programs are written the way a person would write them rather than reduced to one construct each, because the interesting failures are in the interaction: a generator whose frame holds a closure cell, a method that returns a comprehension over an instance attribute. What they avoid is anything kohebi has not got to, and that list is in the runtime's own changelog rather than repeated here, since repeating it is how it goes stale.

Two rules for a file in here:

1. It prints. A program that computes the right answer and says nothing compares equal to a program that crashed after printing nothing, so every case ends in output.
2. It does not print an address, a dictionary iteration order, or anything else CPython is free to change between runs. `kohebi-compat` normalises addresses and paths, and a case that leans on the normaliser is a case that is testing the normaliser.
