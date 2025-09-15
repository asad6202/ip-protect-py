import os
from typing import Any, Dict, List

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Async PostgreSQL access using a connection pool."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.getenv("DATABASE_URL")
        if not self._dsn:
            raise RuntimeError("DATABASE_URL is not set")
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch(self, sql: str) -> List[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        async with self._pool.acquire() as conn:
            # Use dictionary output
            stmt = await conn.prepare(sql)
            rows = await stmt.fetch()
            results: List[Dict[str, Any]] = [dict(row) for row in rows]
            return results


