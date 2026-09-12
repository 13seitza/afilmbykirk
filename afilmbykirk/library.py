import json
import re
from dataclasses import dataclass
from pathlib import Path


EPISODE_PATTERN = re.compile(
    r"(?i)(?:^|[^a-z0-9])s(?P<season>\d{1,2})[ ._-]*e(?P<episode>\d{1,3})(?:[^a-z0-9]|$)"
)


@dataclass(frozen=True)
class Episode:
    id: str
    season: int
    number: int
    title: str
    filename: str
    relative_path: str
    description: str = ""
    artwork: str = ""
    featured: bool = False
    available: bool = False


def _friendly_title(stem, match):
    remainder = stem[match.end() :].strip(" ._-")
    if not remainder:
        return f"Episode {int(match.group('episode'))}"
    return re.sub(r"[._]+", " ", remainder).strip()


def scan_library(media_dir, extensions):
    root = Path(media_dir).resolve()
    catalog_path = root / "catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        catalog = {}
    metadata_by_id = catalog.get("episodes", {})
    media_by_id = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        match = EPISODE_PATTERN.search(path.stem)
        if not match:
            continue
        season = int(match.group("season"))
        number = int(match.group("episode"))
        episode_id = f"s{season:02d}e{number:02d}"
        media_by_id.setdefault(episode_id, (path, match))

    episodes = []
    episode_ids = set(metadata_by_id) | set(media_by_id)
    for episode_id in episode_ids:
        metadata = metadata_by_id.get(episode_id, {})
        media_match = media_by_id.get(episode_id)
        path, match = media_match if media_match else (None, None)
        season = int(episode_id[1:3])
        number = int(episode_id[4:6])
        artwork = metadata.get("artwork", "")
        if artwork and not (root / artwork).is_file():
            artwork = ""
        episodes.append(
            Episode(
                id=episode_id,
                season=season,
                number=number,
                title=metadata.get("title")
                or (_friendly_title(path.stem, match) if path else f"Episode {number}"),
                filename=path.name if path else "",
                relative_path=path.relative_to(root).as_posix() if path else "",
                description=metadata.get("description", ""),
                artwork=artwork,
                featured=bool(metadata.get("featured", False)),
                available=path is not None,
            )
        )
    return sorted(episodes, key=lambda item: (item.season, item.number, item.filename))


def group_by_season(episodes):
    seasons = {}
    for episode in episodes:
        seasons.setdefault(episode.season, []).append(episode)
    return seasons


def find_episode(episodes, episode_id):
    return next((episode for episode in episodes if episode.id == episode_id), None)
