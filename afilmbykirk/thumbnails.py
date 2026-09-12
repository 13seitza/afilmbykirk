import os
import subprocess
from pathlib import Path


def generated_thumbnail_path(media_dir, episode_id):
    return Path(media_dir) / "generated-artwork" / f"{episode_id}.jpg"


def video_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return max(0.0, float(result.stdout.strip()))


def generate_thumbnail(media_dir, episode, position=None):
    if not episode.available:
        return None

    root = Path(media_dir).resolve()
    source = (root / episode.relative_path).resolve()
    if root not in source.parents or not source.is_file():
        return None

    destination = generated_thumbnail_path(root, episode.id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if position is None:
        position = video_duration(source) * 0.25
    position = max(0.0, float(position))

    temporary = destination.with_name(f".{destination.stem}.tmp.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{position:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(960,iw)':-2",
                "-q:v",
                "3",
                "-y",
                str(temporary),
            ],
            check=True,
            timeout=90,
        )
        os.replace(temporary, destination)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        temporary.unlink(missing_ok=True)
        return None
    return destination
