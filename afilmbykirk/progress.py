from .db import get_db


def all_progress():
    rows = get_db().execute("SELECT * FROM playback_progress").fetchall()
    return {row["episode_id"]: dict(row) for row in rows}


def save_progress(episode_id, position, duration, completed=False):
    database = get_db()
    database.execute(
        """
        INSERT INTO playback_progress
            (episode_id, position_seconds, duration_seconds, completed, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(episode_id) DO UPDATE SET
            position_seconds = excluded.position_seconds,
            duration_seconds = excluded.duration_seconds,
            completed = excluded.completed,
            updated_at = CURRENT_TIMESTAMP
        """,
        (episode_id, position, duration, int(completed)),
    )
    database.commit()
