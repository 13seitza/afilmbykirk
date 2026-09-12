from .db import get_db


def get_boolean(key, default=True):
    row = get_db().execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return default
    return row["value"] == "true"


def set_boolean(key, value):
    database = get_db()
    database.execute(
        """
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, "true" if value else "false"),
    )
    database.commit()
