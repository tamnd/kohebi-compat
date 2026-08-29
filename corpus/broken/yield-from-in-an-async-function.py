import asyncio


async def gather(sources):
    for source in sources:
        yield from source


asyncio.run(gather([]))
