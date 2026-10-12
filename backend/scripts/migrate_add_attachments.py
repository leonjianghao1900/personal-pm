"""Create attachments table for task/cost/inbox attachment storage."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrate(engine: Engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("attachments"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type VARCHAR(20) NOT NULL,
                    entity_id INTEGER NOT NULL,
                    original_name VARCHAR(255) NOT NULL,
                    mime VARCHAR(100) DEFAULT 'application/octet-stream',
                    size INTEGER NOT NULL,
                    stored_path VARCHAR(500) NOT NULL,
                    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            "CREATE INDEX ix_attachments_entity_type ON attachments (entity_type)"
        )
        conn.execute(
            "CREATE INDEX ix_attachments_entity_id ON attachments (entity_id)"
        )
        conn.execute(
            "CREATE INDEX ix_attachments_entity ON attachments (entity_type, entity_id)"
        )
