import datetime as dt

from sqlalchemy import create_engine, inspect

from bot.core.db import _migrate_all_day


def test_all_day_migration_preserves_rows_and_marks_local_midnight():
    database_engine = create_engine("sqlite:///:memory:")
    with database_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE plans ("
            "id INTEGER PRIMARY KEY, "
            "ts_utc DATETIME NOT NULL"
            ")"
        )
        connection.exec_driver_sql(
            "INSERT INTO plans (id, ts_utc) VALUES (?, ?), (?, ?)",
            (
                1,
                dt.datetime(2030, 1, 1, 21, 0).isoformat(" "),
                2,
                dt.datetime(2030, 1, 2, 9, 0).isoformat(" "),
            ),
        )

    _migrate_all_day(database_engine)

    columns = {
        column["name"] for column in inspect(database_engine).get_columns("plans")
    }
    with database_engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT id, is_all_day FROM plans ORDER BY id"
        ).fetchall()

    assert "is_all_day" in columns
    assert rows == [(1, 1), (2, 0)]
