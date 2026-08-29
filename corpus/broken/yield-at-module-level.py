def read_all(handle):
    while True:
        block = handle.read(4096)
        if not block:
            break
        yield block


for line in open("input.txt"):
    yield line.rstrip()
