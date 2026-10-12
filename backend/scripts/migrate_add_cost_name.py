"""Add required names to existing costs and backfill legacy rows."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrate(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("costs"):
        return

    columns = {column["name"] for column in inspector.get_columns("costs")}
    with engine.begin() as conn:
        if "name" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE costs ADD COLUMN name "
                    "VARCHAR(200) NOT NULL DEFAULT ''"
                )
            )

        conn.execute(
            text(
                """
                UPDATE costs
                SET name = SUBSTR(
                    CASE
                        WHEN description IS NOT NULL AND TRIM(description) <> ''
                            THEN TRIM(description)
                        ELSE category
                    END,
                    1,
                    200
                )
                WHERE TRIM(name) = ''
                """
            )
        )
