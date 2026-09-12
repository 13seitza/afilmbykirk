import os
from pathlib import Path

from flask import Flask

from .db import init_app as init_database
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    default_media = Path(app.root_path).parent / "media"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("AFBK_SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get(
            "AFBK_DATABASE", str(Path(app.instance_path) / "afilmbykirk.sqlite3")
        ),
        MEDIA_DIR=os.environ.get("AFBK_MEDIA_DIR", str(default_media)),
        HOST=os.environ.get("AFBK_HOST", "127.0.0.1"),
        PORT=int(os.environ.get("AFBK_PORT", "5000")),
        PUBLIC_URL=os.environ.get("AFBK_PUBLIC_URL", ""),
        IDLE_TIMEOUT_SECONDS=int(os.environ.get("AFBK_IDLE_TIMEOUT_SECONDS", "600")),
        DEBUG=os.environ.get("FLASK_DEBUG", "0") == "1",
        SUPPORTED_MEDIA_EXTENSIONS={".mp4", ".m4v", ".webm", ".mkv"},
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["MEDIA_DIR"]).mkdir(parents=True, exist_ok=True)

    init_database(app)
    app.register_blueprint(bp)
    return app
