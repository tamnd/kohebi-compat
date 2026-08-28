async def f():
    async with a as b:
        pass
    async for c in d:
        await c
