import asyncio


def resolve(urls):
    return [await asyncio.sleep(0, url) for url in urls]
