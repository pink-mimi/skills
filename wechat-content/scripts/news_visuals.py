from __future__ import annotations

from pathlib import Path

from PIL import Image

WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def choose_news_visual(run_at, config: dict, assets_root: Path) -> dict:
    key = WEEKDAY_KEYS[run_at.weekday()]
    data = config["news_visuals"]["weekdays"].get(key)
    reason = ""
    if not data:
        data = config["news_visuals"]["default"]
        reason = "weekday_theme_missing"
    result = dict(data)
    result["weekday"] = key
    result["fallback_reason"] = reason
    result["cover_path"] = assets_root / result["cover"]
    result["overview_path"] = assets_root / result["overview"]
    return result


def valid_live_pair(directory: Path | None, maximum_bytes: int) -> bool:
    if not directory:
        return False
    paths = (directory / "cover.png", directory / "overview.png")
    try:
        for path in paths:
            if not path.exists() or path.stat().st_size > maximum_bytes:
                return False
            with Image.open(path) as image:
                image.verify()
        return True
    except (OSError, ValueError):
        return False
