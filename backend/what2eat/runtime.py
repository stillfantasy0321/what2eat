import asyncio


def selector_loop_factory():
    """Return the loop required by Psycopg's async implementation on Windows."""
    return asyncio.SelectorEventLoop()
