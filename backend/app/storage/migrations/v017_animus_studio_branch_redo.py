"""v017: persist the redo stack per Studio branch.

Undo/redo used to live only in the in-memory ``RevisionStore``. After a restart the branch head was
durable but the redo stack was not, so a user could undo, restart, and lose the ability to redo.
The stack is branch-scoped and is stored as a compact JSON list of version ids.

This migration is additive: it only adds a column with a default and never rewrites existing rows.
"""

VERSION = 17
DESCRIPTION = "Persist ANIMUS Studio branch redo stacks"

_COLUMN = "redo_json"
_DEFAULT = "'[]'"


async def upgrade(db) -> None:
    cursor = await db.execute("PRAGMA table_info(animus_studio_branches)")
    columns = await cursor.fetchall()
    if not columns:
        # The Studio tables are created by v014/v015. Reaching v017 without a branch table means the
        # database was assembled outside the migration runner; fail loudly instead of creating an
        # incompatible partial schema.
        raise RuntimeError("animus_studio_branches is missing; run the earlier migrations first")

    names = {row[1] for row in columns}
    if _COLUMN not in names:
        await db.execute(
            f"ALTER TABLE animus_studio_branches ADD COLUMN {_COLUMN} TEXT NOT NULL DEFAULT {_DEFAULT}"
        )
    await db.commit()
