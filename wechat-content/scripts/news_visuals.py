from __future__ import annotations

from pathlib import Path

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
