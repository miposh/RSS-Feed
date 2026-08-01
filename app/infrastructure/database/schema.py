"""
Database schema management and migrations.

Migration files are discovered automatically from ``app/migrations`` and applied
in filename order. Applied migrations are recorded in the ``schema_migrations``
table, so every migration runs exactly once per database.
"""
import logging
from pathlib import Path

from app.infrastructure.database.connection.base import BaseConnection

logger = logging.getLogger(__name__)


class DatabaseSchema:
    SQL_DIR = Path(__file__).parent.parent.parent / "migrations"
    TRACKING_TABLE = "schema_migrations"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    def discover_migrations(self) -> list[Path]:
        """Return every migration file, ordered by filename (001_, 002_, ...)."""
        if not self.SQL_DIR.is_dir():
            logger.error(f"Migrations directory not found: {self.SQL_DIR}")
            return []

        return sorted(self.SQL_DIR.glob("*.sql"), key=lambda path: path.name)

    async def _ensure_tracking_table(self) -> None:
        await self.connection.execute(
            sql=f"""
                CREATE TABLE IF NOT EXISTS {self.TRACKING_TABLE} (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """
        )

    async def _get_applied(self) -> set[str]:
        result = await self.connection.fetchmany(
            sql=f"SELECT name FROM {self.TRACKING_TABLE}"
        )
        return {row["name"] for row in result.data}

    async def apply_migrations(self) -> list[str]:
        """Apply every migration that has not been applied yet.

        Returns:
            Names of the migrations applied during this call.
        """
        await self._ensure_tracking_table()
        applied = await self._get_applied()

        pending = [path for path in self.discover_migrations() if path.name not in applied]

        if not pending:
            logger.info("Database schema is up to date (%d migration(s) applied)", len(applied))
            return []

        logger.info(f"Applying {len(pending)} pending migration(s)...")

        for file_path in pending:
            try:
                await self.connection.execute(sql=file_path.read_text(encoding="utf-8"))
                await self.connection.execute(
                    sql=f"INSERT INTO {self.TRACKING_TABLE}(name) VALUES(%s) ON CONFLICT DO NOTHING",
                    params=(file_path.name,),
                )
                logger.info(f"✓ Applied: {file_path.name}")
            except Exception as e:
                logger.error(f"✗ Failed to apply {file_path.name}: {e}")
                raise

        logger.info("All migrations applied successfully!")
        return [path.name for path in pending]
