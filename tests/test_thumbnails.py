from types import SimpleNamespace
from unittest.mock import patch

from afilmbykirk.thumbnails import generate_thumbnail, generated_thumbnail_path


def test_generated_thumbnail_uses_episode_id(tmp_path):
    assert generated_thumbnail_path(tmp_path, "s01e02") == (
        tmp_path / "generated-artwork" / "s01e02.jpg"
    )


def test_thumbnail_is_extracted_at_requested_position(tmp_path):
    source = tmp_path / "Season 01" / "S01E01.mkv"
    source.parent.mkdir()
    source.touch()
    episode = SimpleNamespace(
        id="s01e01", available=True, relative_path="Season 01/S01E01.mkv"
    )

    def fake_run(command, **_kwargs):
        output = command[-1]
        if command[0] == "ffmpeg":
            with open(output, "wb") as image:
                image.write(b"jpeg")
        return SimpleNamespace(stdout="")

    with patch("afilmbykirk.thumbnails.subprocess.run", side_effect=fake_run) as run:
        result = generate_thumbnail(tmp_path, episode, 42.25)

    assert result.read_bytes() == b"jpeg"
    ffmpeg_command = run.call_args.args[0]
    assert ffmpeg_command[ffmpeg_command.index("-ss") + 1] == "42.250"
