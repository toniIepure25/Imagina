"""v016: additive indexes for the Studio candidate lifecycle and library ordering.

No table is rebuilt and no column is changed. This migration only makes the new source-scoped
candidate queries and the recent-session/world lists index-backed on existing databases.
"""

VERSION = 16
DESCRIPTION = "ANIMUS Studio candidate lifecycle and listing indexes"

STATEMENTS = [
    """CREATE INDEX IF NOT EXISTS idx_studio_candidates_source
       ON animus_studio_candidates(session_id, source_version_id, selected, created_at)""",
    """CREATE INDEX IF NOT EXISTS idx_studio_sessions_updated
       ON animus_studio_sessions(updated_at)""",
    """CREATE INDEX IF NOT EXISTS idx_studio_worlds_created
       ON animus_studio_worlds(created_at)""",
]


async def upgrade(db) -> None:
    for statement in STATEMENTS:
        await db.execute(statement)
    await db.commit()
