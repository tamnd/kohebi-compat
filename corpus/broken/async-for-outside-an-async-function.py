def collect(stream):
    out = []
    async for chunk in stream:
        out.append(chunk)
    return out
