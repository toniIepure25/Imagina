import os

import aiosqlite

DB_PATH = os.environ.get("IMAGINA_DB_PATH", "data/imagina.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    cursor = await db.execute("PRAGMA foreign_keys")
    row = await cursor.fetchone()
    if not row or row[0] != 1:
        raise RuntimeError("SQLite foreign_keys PRAGMA could not be enabled")
    return db


async def init_db():
    from app.storage.migration_runner import run_migrations

    db = await get_db()
    try:
        await run_migrations(db)
    finally:
        await db.close()
