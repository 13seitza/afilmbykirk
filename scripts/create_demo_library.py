#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    root = project_root / "demo-media"
    catalog_source = project_root / "media.example" / "catalog.json"
    catalog = json.loads(catalog_source.read_text())
    root.mkdir(exist_ok=True)
    for placeholder in root.rglob("*.mp4"):
        if placeholder.stat().st_size == 0:
            placeholder.unlink()
    (root / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")

    for episode_id in catalog["episodes"]:
        season = int(episode_id[1:3])
        season_dir = root / f"Season {season:02d}"
        season_dir.mkdir(exist_ok=True)
        (season_dir / f"{episode_id}.mp4").touch()

    database_path = root / "demo.sqlite3"
    database = sqlite3.connect(database_path)
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS playback_progress (
            episode_id TEXT PRIMARY KEY,
            position_seconds REAL NOT NULL DEFAULT 0,
            duration_seconds REAL NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    database.execute(
        """
        INSERT INTO playback_progress
            (episode_id, position_seconds, duration_seconds, completed, updated_at)
        VALUES ('s03e02', 1032, 2520, 0, CURRENT_TIMESTAMP)
        ON CONFLICT(episode_id) DO UPDATE SET
            position_seconds = 1032,
            duration_seconds = 2520,
            completed = 0,
            updated_at = CURRENT_TIMESTAMP
        """
    )
    database.commit()
    database.close()

    count = len(catalog["episodes"])
    print(f"Created {count} demo episodes in {root}")
    print("The demo resume card is seeded at Season 3, Episode 2 — 17 minutes.")


if __name__ == "__main__":
    main()
