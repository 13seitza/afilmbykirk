#!/usr/bin/env python3
import argparse
import json
import platform
import subprocess
from pathlib import Path


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name", "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    streams = json.loads(result.stdout).get("streams", [])
    return {stream.get("codec_type"): stream.get("codec_name") for stream in streams}


def command(source, temporary):
    base = ["ffmpeg", "-hide_banner", "-stats"]
    if platform.system() == "Darwin":
        base.extend(["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox_vld"])
    base.extend(["-i", str(source), "-map", "0:v:0", "-map", "0:a:0"])
    if platform.system() == "Darwin":
        base.extend([
            "-c:v", "h264_videotoolbox", "-b:v", "5M",
            "-maxrate", "7M", "-bufsize", "10M",
        ])
    else:
        base.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"])
    base.extend(["-c:a", "copy", "-movflags", "+faststart", "-y", str(temporary)])
    return base


def convert(source, delete_original):
    destination = source.with_suffix(".mp4")
    temporary = source.with_name(f".{source.stem}.converting.mp4")
    if destination.exists():
        codecs = probe(destination)
        if codecs.get("video") == "h264" and codecs.get("audio") in {"aac", "mp3"}:
            print(f"READY {destination.name}", flush=True)
            if delete_original:
                source.unlink()
            return
        raise RuntimeError(f"Refusing to overwrite incompatible {destination}")

    temporary.unlink(missing_ok=True)
    print(f"CONVERTING {source.name}", flush=True)
    try:
        subprocess.run(command(source, temporary), check=True)
        codecs = probe(temporary)
        if codecs.get("video") != "h264" or codecs.get("audio") not in {"aac", "mp3"}:
            raise RuntimeError(f"Validation failed for {source.name}: {codecs}")
        temporary.replace(destination)
        if delete_original:
            source.unlink()
        print(f"COMPLETE {destination.name}", flush=True)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Convert media to browser-safe H.264 MP4")
    parser.add_argument("root", type=Path)
    parser.add_argument("--delete-originals", action="store_true")
    args = parser.parse_args()
    sources = sorted(args.root.expanduser().resolve().rglob("*.mkv"))
    if not sources:
        raise SystemExit("No MKV files found")
    print(f"Queued {len(sources)} file(s)", flush=True)
    for source in sources:
        convert(source, args.delete_originals)


if __name__ == "__main__":
    main()
