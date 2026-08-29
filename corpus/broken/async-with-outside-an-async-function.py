import asyncio


def session(pool):
    async with pool.acquire() as conn:
        return conn.fetch("select 1")


asyncio.run(session(None))
