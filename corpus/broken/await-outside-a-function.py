import asyncio


async def fetch(url):
    await asyncio.sleep(0)
    return url


result = await fetch("http://example.invalid")
