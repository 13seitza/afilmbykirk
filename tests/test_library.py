import json
from pathlib import Path

from afilmbykirk.library import scan_library


def test_scan_library_parses_and_sorts_episode_names(tmp_path):
    (tmp_path / "Season 2").mkdir()
    (tmp_path / "Season 2" / "Gilmore.Girls.S02E03.Red.Light.mp4").touch()
    (tmp_path / "S01E02 - The Lorelais First Day.m4v").touch()
    (tmp_path / "notes.txt").touch()

    episodes = scan_library(tmp_path, {".mp4", ".m4v"})

    assert [episode.id for episode in episodes] == ["s01e02", "s02e03"]
    assert episodes[0].title == "The Lorelais First Day"
    assert episodes[1].relative_path.startswith("Season 2/")


def test_unparseable_video_is_ignored(tmp_path):
    Path(tmp_path / "movie.mp4").touch()
    assert scan_library(tmp_path, {".mp4"}) == []


def test_catalog_overrides_title_and_adds_metadata(tmp_path):
    (tmp_path / "S01E01 - Filename Title.mp4").touch()
    (tmp_path / "catalog.json").write_text(
        json.dumps(
            {
                "episodes": {
                    "s01e01": {
                        "title": "Catalog Title",
                        "description": "A description",
                        "artwork": "artwork/s01e01.jpg",
                        "featured": True,
                    }
                }
            }
        )
    )
    episode = scan_library(tmp_path, {".mp4"})[0]
    assert episode.title == "Catalog Title"
    assert episode.description == "A description"
    assert episode.featured is True


def test_catalog_episode_exists_without_video(tmp_path):
    (tmp_path / "catalog.json").write_text(
        json.dumps(
            {"episodes": {"s01e01": {"title": "Pilot", "description": "First."}}}
        )
    )
    episode = scan_library(tmp_path, {".mp4"})[0]
    assert episode.title == "Pilot"
    assert episode.available is False
