import sys


TIMEOUT = 30


def connect(host, port):
    return host, port


if len(sys.argv) < 2:
    print("usage: connect HOST [PORT]")
    return 1
