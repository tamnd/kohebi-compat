# Hand written corpus

The default corpus for `kohebi-compat tokens` is the standard library of the
oracle interpreter, which is thousands of files of ordinary Python. Ordinary is
the problem. Real code is written by people who use four spaces, avoid tabs,
and do not put a form feed in the middle of a class body, so a corpus of real
code exercises the easy half of a tokenizer very thoroughly and the hard half
not at all.

These files are the hard half. Each one is a valid Python program, so CPython
tokenizes it and we can compare, and each one exists to hit something the
standard library does not.
