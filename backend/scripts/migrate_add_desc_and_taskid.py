"""一次性迁移：为 projects 加 description，为 costs 加 task_id。

幂等：字段已存在则跳过。在 lifespan 中 Base.metadata.create_all 之后调用。
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import engine


def table_exists(eng: Engine, table_name: str) -> bool:
    return inspect(eng).has_table(table_name)


def column_exists(eng: Engine, table_name: str, column_name: str) -> bool:
    if not table_exists(eng, table_name):
        return False
    cols = {c["name"] for c in inspect(eng).get_columns(table_name)}
    return column_name in cols


def migrate(engine: Engine) -> None:
    if column_exists(engine, "projects", "description"):
        return  # nothing to do (also covers no-table fresh DB)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE projects ADD COLUMN description VARCHAR(2000)"))

    if not column_exists(engine, "costs", "task_id"):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE costs ADD COLUMN task_id INTEGER"))

    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_costs_task_id ON costs (task_id)"))


if __name__ == "__main__":
    migrate(engine)
    print("migration done")