import io
from unittest.mock import patch

import pytest

from afilmbykirk import create_app


@pytest.fixture()
def app(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "S01E01 - Pilot.mp4").write_bytes(b"fake-video-data")
    return create_app(
        {
            "TESTING": True,
            "MEDIA_DIR": str(media),
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "PUBLIC_URL": "http://afilmbykirk.local:5000/",
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def test_home_lists_discovered_episode(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"choose a season" in response.data
    assert b'href="/season/1"' in response.data
    assert b"Start watching" in response.data
    assert b"Kirk" in response.data
    assert b"coffee and love" not in response.data
    assert b'id="sleep-screen"' in response.data
    assert b'class="feature-card continue-card remote-focus has-artwork"' in response.data
    assert b'class="season-tile remote-focus has-artwork"' in response.data
    assert response.data.count(b'/artwork/s01e01') == 2


def test_season_page_lists_episodes_and_play_options(client):
    response = client.get("/season/1")
    assert response.status_code == 200
    assert b"Pilot" in response.data
    assert b"Play season" in response.data
    assert b"Play random" in response.data
    assert b"Go back" in response.data


def test_random_season_redirects_within_that_season(client):
    response = client.get("/random/season/1")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/watch/s01e01")


def test_player_advances_across_season_boundary(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "S01E22 - Finale.mp4").touch()
    (media / "S02E01 - Premiere.mp4").touch()
    app = create_app(
        {
            "TESTING": True,
            "MEDIA_DIR": str(media),
            "DATABASE": str(tmp_path / "test.sqlite3"),
        }
    )
    response = app.test_client().get("/watch/s01e22")
    assert b'data-next-url="/watch/s02e01"' in response.data


def test_media_is_served_conditionally(client):
    response = client.get("/media/s01e01", headers={"Range": "bytes=0-3"})
    assert response.status_code == 206
    assert response.data == b"fake"


def test_player_is_fullscreen_with_streaming_controls(client):
    response = client.get("/watch/s01e01")
    assert b'class="cinema-player"' in response.data
    assert b'id="play-button"' in response.data
    assert b'id="rewind-button"' not in response.data
    assert b"Enter: pause" not in response.data
    assert b"Back to season" in response.data
    assert b'id="thumbnail-button"' in response.data
    assert b"Save thumbnail" in response.data


def test_paused_frame_can_be_saved_as_thumbnail(client, app):
    generated = app.config["MEDIA_DIR"] + "/generated-artwork/s01e01.jpg"
    with patch("afilmbykirk.routes.generate_thumbnail", return_value=generated) as create:
        response = client.post("/api/thumbnail/s01e01", json={"position": 321.5})

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert create.call_args.args[2] == 321.5


def test_thumbnail_capture_is_restricted_to_tv(client):
    response = client.post(
        "/api/thumbnail/s01e01",
        json={"position": 10},
        environ_base={"REMOTE_ADDR": "192.168.1.20"},
    )
    assert response.status_code == 403


def test_progress_is_saved_and_shown(client):
    response = client.post(
        "/api/progress/s01e01", json={"position": 120, "duration": 2400}
    )
    assert response.get_json() == {"ok": True, "completed": False}
    assert b"Continue where you left off" in client.get("/").data


def test_progress_rejects_invalid_values(client):
    response = client.post(
        "/api/progress/s01e01", json={"position": "nope", "duration": 100}
    )
    assert response.status_code == 400


def test_qr_uses_public_url(client):
    response = client.get("/connect/qr.png")
    assert response.status_code == 200
    assert response.content_type == "image/png"
    assert len(io.BytesIO(response.data).getvalue()) > 100


def test_connect_screen_is_minimal(client):
    response = client.get("/connect")
    assert b"Watch on another device" in response.data
    assert b"No television" not in response.data
    assert b"Playback happens" not in response.data


def test_local_tv_can_open_settings(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Scan for networks" in response.data
    assert b"Button tester" in response.data
    assert b"Audio settings" in response.data


def test_audio_settings_include_outputs_and_bluetooth(client):
    with patch("afilmbykirk.routes.audio_outputs", return_value=[]):
        response = client.get("/settings/audio")
    assert response.status_code == 200
    assert b"Audio output" in response.data
    assert b"Pair Bluetooth speaker" in response.data


def test_background_video_can_be_disabled(client):
    assert b'class="ambient-video"' in client.get("/").data
    response = client.post(
        "/api/settings/background-video", json={"enabled": False}
    )
    assert response.get_json() == {"ok": True, "enabled": False}
    assert b'class="ambient-video"' not in client.get("/").data
    assert b"Currently off" in client.get("/settings").data


def test_settings_are_not_available_to_lan_clients(client):
    response = client.get(
        "/settings", environ_base={"REMOTE_ADDR": "192.168.1.20"}
    )
    assert response.status_code == 403


def test_volume_action_uses_system_control(client):
    with patch(
        "afilmbykirk.routes.change_volume",
        return_value={"available": True, "percent": 55, "muted": False},
    ) as change:
        response = client.post("/api/volume", json={"action": "up"})
    assert response.get_json()["percent"] == 55
    change.assert_called_once_with("up")


def test_catalog_episodes_display_without_media(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "catalog.json").write_text(
        '{"episodes":{"s01e01":{"title":"Pilot","description":"The beginning."}}}'
    )
    app = create_app(
        {
            "TESTING": True,
            "MEDIA_DIR": str(media),
            "DATABASE": str(tmp_path / "test.sqlite3"),
        }
    )
    client = app.test_client()

    assert b'href="/season/1"' in client.get("/").data
    season = client.get("/season/1")
    assert b"Pilot" in season.data
    assert b"Gilmore Girls" in season.data
    assert b"Media not loaded" in season.data
    unavailable = client.get("/watch/s01e01")
    assert unavailable.status_code == 200
    assert b"Media not available" in unavailable.data
    assert b'href="/random"' in client.get("/").data
