for size in (1, 2, 4):

    class Buffer:
        capacity = size

        if capacity > 2:
            break

    print(Buffer.capacity)
