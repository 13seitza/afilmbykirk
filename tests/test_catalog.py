import json
from collections import Counter
from pathlib import Path


def test_complete_catalog_has_all_original_series_episodes():
    path = Path(__file__).parent.parent / "media.example" / "catalog.json"
    catalog = json.loads(path.read_text())
    episodes = catalog["episodes"]

    assert len(episodes) == 153
    assert set(episodes) == {
        f"s{season:02d}e{episode:02d}"
        for season, count in {
            1: 21,
            2: 22,
            3: 22,
            4: 22,
            5: 22,
            6: 22,
            7: 22,
        }.items()
        for episode in range(1, count + 1)
    }
    assert Counter(int(key[1:3]) for key in episodes) == {
        1: 21,
        2: 22,
        3: 22,
        4: 22,
        5: 22,
        6: 22,
        7: 22,
    }
    assert all(item["title"] and item["description"] for item in episodes.values())
    assert catalog["_meta"]["source"] == "TVmaze"
