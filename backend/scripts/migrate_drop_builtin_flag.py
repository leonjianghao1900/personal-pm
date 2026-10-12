"""一次性迁移：把现有 is_builtin=true 的类别改为 false（不再有内置概念）。幂等。"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def column_exists(eng: Engine, table_name: str, column_name: str) -> bool:
    if not inspect(eng).has_table(table_name):
        return False
    cols = {c["name"] for c in inspect(eng).get_columns(table_name)}
    return column_name in cols


def migrate(engine: Engine) -> None:
    if not column_exists(engine, "cost_categories", "is_builtin"):
        return
    with engine.begin() as conn:
        conn.execute(text("UPDATE cost_categories SET is_builtin = 0 WHERE is_builtin = 1"))


if __name__ == "__main__":
    from app.database import engine
    migrate(engine)
    print("drop builtin flag done")
