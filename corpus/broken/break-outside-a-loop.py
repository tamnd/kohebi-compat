import os


def listing(root):
    for name in os.listdir(root):
        if name.startswith("."):
            continue
        yield name


if not os.path.isdir("."):
    break
