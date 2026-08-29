def totals(rows):
    return sum((yield row) for row in rows)
