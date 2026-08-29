import asyncio


async def outer(urls):
    def inner(url):
        return await asyncio.sleep(0, url)

    return [inner(url) for url in urls]
