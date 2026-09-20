import asyncio
import sys
from pathlib import Path
from langgraph.store.postgres import AsyncPostgresStore
from what2eat.config import Settings
from what2eat.db.pool import open_pool


async def migrate(dsn: str) -> None:
    pool = await open_pool(dsn)
    try:
        async with pool.connection() as conn:
            # Session lock covers Store's out-of-transaction migrations as well.
            await conn.execute('SELECT pg_advisory_lock(78243109)')
            try:
                async with conn.transaction():
                    await conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version text PRIMARY KEY, applied_at timestamptz DEFAULT now())')
                    for path in sorted((Path(__file__).parent / 'migrations').glob('*.sql')):
                        row = await (await conn.execute('SELECT version FROM schema_migrations WHERE version=%s', (path.name,))).fetchone()
                        if row is None:
                            await conn.execute(path.read_text(encoding='utf-8'), prepare=False)
                            await conn.execute('INSERT INTO schema_migrations(version) VALUES (%s)', (path.name,))
                await AsyncPostgresStore(conn, index=None).setup()
            finally:
                await conn.execute('SELECT pg_advisory_unlock(78243109)')
    finally:
        await pool.close()


def run_migration(dsn: str) -> None:
    """Run migrations with the event loop supported by Psycopg on Windows."""
    if sys.platform == 'win32':
        asyncio.run(migrate(dsn), loop_factory=asyncio.SelectorEventLoop)
        return
    asyncio.run(migrate(dsn))


if __name__ == '__main__':
    settings = Settings()
    if not settings.database_url:
        raise SystemExit('请先在本机 .env 配置 DATABASE_URL')
    run_migration(settings.database_url.get_secret_value())
    print('what2eat 数据库迁移完成（含偏好 Store）。')
