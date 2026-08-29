def paginate(rows, size):
    return [(yield rows[at:at + size]) for at in range(0, len(rows), size)]
