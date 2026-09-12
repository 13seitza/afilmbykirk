import io
import random
from pathlib import Path

import qrcode
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from .library import find_episode, group_by_season, scan_library
from .progress import all_progress, save_progress
from .preferences import get_boolean, set_boolean
from .thumbnails import generate_thumbnail, generated_thumbnail_path
from .system_controls import (
    ControlError,
    audio_outputs,
    change_volume,
    connect_bluetooth,
    connect_wifi,
    power_action,
    scan_wifi,
    scan_bluetooth,
    select_audio_output,
    volume_status,
    wifi_status,
)


bp = Blueprint("main", __name__)


def local_request_only():
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        abort(403)


def library():
    return scan_library(
        current_app.config["MEDIA_DIR"],
        current_app.config["SUPPORTED_MEDIA_EXTENSIONS"],
    )


def hero_background_path():
    custom_path = Path(current_app.config["MEDIA_DIR"]) / "branding" / "hero-background.mp4"
    if custom_path.is_file():
        return custom_path
    return Path(current_app.root_path) / "static" / "video" / "hero-background.mp4"


@bp.get("/")
def home():
    episodes = library()
    progress = all_progress()
    continue_watching = [
        episode
        for episode in episodes
        if episode.available
        and episode.id in progress
        and progress[episode.id]["position_seconds"] > 10
        and not progress[episode.id]["completed"]
    ]
    continue_watching.sort(
        key=lambda episode: progress[episode.id]["updated_at"], reverse=True
    )
    return render_template(
        "home.html",
        seasons=group_by_season(episodes),
        episode_count=len(episodes),
        available_count=sum(episode.available for episode in episodes),
        continue_watching=continue_watching[:6],
        progress=progress,
        hero_video=(
            hero_background_path().is_file()
            and get_boolean("background_video_enabled", True)
        ),
        featured=next((episode for episode in episodes if episode.featured), None),
        first_episode=next(
            (episode for episode in episodes if episode.available),
            episodes[0] if episodes else None,
        ),
    )


@bp.get("/watch/<episode_id>")
def watch(episode_id):
    episodes = library()
    episode = find_episode(episodes, episode_id)
    if episode is None:
        abort(404)
    progress = all_progress().get(episode_id, {})
    index = episodes.index(episode)
    next_episode = next(
        (candidate for candidate in episodes[index + 1 :] if candidate.available),
        None,
    )
    return render_template(
        "watch.html", episode=episode, progress=progress, next_episode=next_episode
    )


@bp.get("/season/<int:season_number>")
def season(season_number):
    episodes = [
        episode for episode in library() if episode.season == season_number
    ]
    if not episodes:
        abort(404)
    return render_template(
        "season.html",
        season_number=season_number,
        episodes=episodes,
        available_episodes=[episode for episode in episodes if episode.available],
        progress=all_progress(),
    )


@bp.get("/random")
def random_episode():
    all_episodes = library()
    episodes = [episode for episode in all_episodes if episode.available] or all_episodes
    if not episodes:
        return redirect(url_for("main.home"))
    return redirect(url_for("main.watch", episode_id=random.choice(episodes).id))


@bp.get("/random/season/<int:season_number>")
def random_season_episode(season_number):
    season_episodes = [
        episode
        for episode in library()
        if episode.season == season_number
    ]
    episodes = [episode for episode in season_episodes if episode.available] or season_episodes
    if not episodes:
        abort(404)
    return redirect(url_for("main.watch", episode_id=random.choice(episodes).id))


@bp.get("/media/<episode_id>")
def media(episode_id):
    episode = find_episode(library(), episode_id)
    if episode is None or not episode.available:
        abort(404)
    root = Path(current_app.config["MEDIA_DIR"]).resolve()
    media_path = (root / episode.relative_path).resolve()
    if root not in media_path.parents or not media_path.is_file():
        abort(404)
    return send_file(media_path, conditional=True)


@bp.get("/branding/hero-background.mp4")
def hero_background():
    path = hero_background_path().resolve()
    if not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


@bp.get("/artwork/<episode_id>")
def artwork(episode_id):
    episode = find_episode(library(), episode_id)
    if episode is None:
        abort(404)
    root = Path(current_app.config["MEDIA_DIR"]).resolve()
    generated = generated_thumbnail_path(root, episode.id)
    if generated.is_file():
        path = generated.resolve()
    elif episode.artwork:
        path = (root / episode.artwork).resolve()
    else:
        path = generate_thumbnail(root, episode)
        if path:
            path = path.resolve()
    if not path:
        abort(404)
    if root not in path.parents or not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


@bp.post("/api/thumbnail/<episode_id>")
def save_thumbnail(episode_id):
    local_request_only()
    episode = find_episode(library(), episode_id)
    if episode is None or not episode.available:
        abort(404)
    payload = request.get_json(silent=True) or {}
    try:
        position = float(payload.get("position", 0))
    except (TypeError, ValueError):
        return jsonify(error="position must be a number"), 400
    path = generate_thumbnail(current_app.config["MEDIA_DIR"], episode, position)
    if path is None:
        return jsonify(error="Could not create thumbnail"), 500
    return jsonify(ok=True, artwork=url_for("main.artwork", episode_id=episode.id))


@bp.post("/api/progress/<episode_id>")
def update_progress(episode_id):
    episode = find_episode(library(), episode_id)
    if episode is None or not episode.available:
        abort(404)
    payload = request.get_json(silent=True) or {}
    try:
        position = max(0.0, float(payload.get("position", 0)))
        duration = max(0.0, float(payload.get("duration", 0)))
    except (TypeError, ValueError):
        return jsonify(error="position and duration must be numbers"), 400
    completed = bool(payload.get("completed")) or (
        duration > 0 and position / duration >= 0.92
    )
    save_progress(episode_id, position, duration, completed)
    return jsonify(ok=True, completed=completed)


@bp.get("/connect")
def connect():
    connect_url = current_app.config["PUBLIC_URL"] or request.host_url
    return render_template("connect.html", connect_url=connect_url)


@bp.get("/settings")
def settings():
    local_request_only()
    return render_template(
        "settings.html",
        wifi=wifi_status(),
        background_video_enabled=get_boolean("background_video_enabled", True),
    )


@bp.get("/settings/audio")
def audio_settings():
    local_request_only()
    return render_template(
        "audio.html", volume=volume_status(), audio_outputs=audio_outputs()
    )


@bp.get("/api/wifi")
def wifi_networks():
    local_request_only()
    try:
        return jsonify(ok=True, networks=scan_wifi(), **wifi_status())
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 503


@bp.post("/api/wifi/connect")
def wifi_connect():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    try:
        status = connect_wifi(payload.get("ssid", ""), payload.get("password", ""))
        return jsonify(ok=True, **status)
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 400


@bp.get("/api/volume")
def get_volume():
    local_request_only()
    return jsonify(ok=True, **volume_status())


@bp.post("/api/volume")
def set_volume():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(ok=True, **change_volume(payload.get("action")))
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 400


@bp.post("/api/settings/background-video")
def set_background_video():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get("enabled"), bool):
        return jsonify(error="enabled must be true or false"), 400
    set_boolean("background_video_enabled", payload["enabled"])
    return jsonify(ok=True, enabled=payload["enabled"])


@bp.post("/api/system/power")
def system_power():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    try:
        power_action(payload.get("action"))
        return jsonify(ok=True)
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 400


@bp.get("/api/audio/outputs")
def get_audio_outputs():
    local_request_only()
    return jsonify(ok=True, outputs=audio_outputs())


@bp.post("/api/audio/output")
def set_audio_output():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(ok=True, outputs=select_audio_output(payload.get("id", "")))
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 400


@bp.get("/api/bluetooth")
def bluetooth_devices():
    local_request_only()
    try:
        return jsonify(ok=True, devices=scan_bluetooth())
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 503


@bp.post("/api/bluetooth/connect")
def bluetooth_connect():
    local_request_only()
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(ok=True, **connect_bluetooth(payload.get("address", "")))
    except ControlError as error:
        return jsonify(ok=False, error=str(error)), 400


@bp.get("/connect/qr.png")
def connect_qr():
    connect_url = current_app.config["PUBLIC_URL"] or request.host_url
    image = qrcode.make(connect_url)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", max_age=30)


@bp.get("/health")
def health():
    return jsonify(ok=True, episodes=len(library()))
