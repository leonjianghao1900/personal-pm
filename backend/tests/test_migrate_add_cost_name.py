from sqlalchemy import create_engine, inspect, text

from scripts.migrate_add_cost_name import migrate


def test_migrate_adds_and_backfills_cost_names_idempotently(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    long_description = "x" * 201

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE costs (
                    id INTEGER PRIMARY KEY,
                    category VARCHAR(20) NOT NULL,
                    description VARCHAR
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO costs (id, category, description) VALUES
                    (1, 'fallback-one', '  Description first  '),
                    (2, 'Category fallback', '   '),
                    (3, 'fallback-three', :long_description)
                """
            ),
            {"long_description": long_description},
        )

    migrate(engine)

    columns = {column["name"]: column for column in inspect(engine).get_columns("costs")}
    assert columns["name"]["nullable"] is False
    with engine.begin() as conn:
        assert conn.execute(text("SELECT id, name FROM costs ORDER BY id")).all() == [
            (1, "Description first"),
            (2, "Category fallback"),
            (3, "x" * 200),
        ]
        conn.execute(
            text("UPDATE costs SET description = 'Changed later' WHERE id = 1")
        )

    migrate(engine)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT name FROM costs WHERE id = 1")).scalar_one() == (
            "Description first"
        )
