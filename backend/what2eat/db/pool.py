from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


async def open_pool(dsn: str) -> AsyncConnectionPool:
    pool = AsyncConnectionPool(dsn, open=False, min_size=1, max_size=5,
        kwargs={'autocommit': True, 'prepare_threshold': 0, 'row_factory': dict_row},
        timeout=10, reconnect_timeout=10)
    try:
        await pool.open()
        await pool.wait(timeout=10)
        return pool
    except BaseException:
        await pool.close()
        raise
