CHUNK = 4096


def read_all(handle):
    while True:
        block = handle.read(CHUNK)
        if not block:
            break
        yield block


for line in open("input.txt"):
    yield line.rstrip()
