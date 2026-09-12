#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


SUPPORTED_SUFFIXES = {".mp4", ".m4v", ".mkv", ".webm"}


def inspect(path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=format_name:stream=codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
    except FileNotFoundError:
        raise SystemExit("ffprobe is not installed. Install ffmpeg first.")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return "UNREADABLE", "ffprobe could not inspect this file"

    codecs = {
        stream.get("codec_type"): stream.get("codec_name")
        for stream in payload.get("streams", [])
    }
    video = codecs.get("video", "none")
    audio = codecs.get("audio", "none")
    containers = payload.get("format", {}).get("format_name", "")
    browser_ready = "mp4" in containers and video == "h264" and audio in {"aac", "mp3"}
    status = "READY" if browser_ready else "CHECK"
    return status, f"container={containers or 'unknown'} video={video} audio={audio}"


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser()
    files = sorted(
        path for path in root.rglob("*") if path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise SystemExit(f"No media files found under {root}")
    for path in files:
        status, details = inspect(path)
        print(f"{status:10} {path.relative_to(root)}  {details}")
    print("\nREADY means the file is the safest format for Chromium, Safari, and mobile.")
    print("CHECK files may work locally but should be tested or converted before the trip.")


if __name__ == "__main__":
    main()
