def drain(stream):
    """Meant to be an `async def`, and the comprehension is what says so."""
    return [chunk async for chunk in stream]
