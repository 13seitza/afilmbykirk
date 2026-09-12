from pathlib import Path
from unittest.mock import patch

from scripts.convert_media import convert


def test_original_is_deleted_only_after_validated_conversion(tmp_path):
    source = tmp_path / "S01E01.mkv"
    source.write_bytes(b"original")

    def fake_run(command, check):
        Path(command[-1]).write_bytes(b"converted")

    with (
        patch("scripts.convert_media.subprocess.run", side_effect=fake_run),
        patch("scripts.convert_media.probe", return_value={"video": "h264", "audio": "aac"}),
    ):
        convert(source, delete_original=True)

    assert not source.exists()
    assert (tmp_path / "S01E01.mp4").read_bytes() == b"converted"
