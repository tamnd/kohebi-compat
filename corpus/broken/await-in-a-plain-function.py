import asyncio


def fetch(url):
    handle = await asyncio.open_connection(url, 80)
    return handle
