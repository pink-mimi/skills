from __future__ import annotations

from datetime import datetime


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def assess_heat(candidate, window_start, window_end):
    start = parse_time(window_start)
    end = parse_time(window_end)
    evidence = []
    for row in candidate.get("heat_evidence") or []:
        if not row.get("url") or not row.get("observed_at"):
            continue
        observed = parse_time(row["observed_at"]).astimezone(start.tzinfo)
        if start <= observed < end:
            evidence.append(dict(row))

    created_at = candidate.get("created_at")
    new_in_window = False
    if created_at:
        created = parse_time(created_at).astimezone(start.tzinfo)
        new_in_window = start <= created < end
    resurgence = any(
        row.get("kind") in {"release", "official_launch", "major_update"}
        for row in evidence
    )
    eligible = bool(evidence)
    if not eligible:
        heat_class = "insufficient"
    elif new_in_window:
        heat_class = "new_breakout"
    elif resurgence:
        heat_class = "mature_resurgence"
    else:
        heat_class = "weekly_breakout"
    return {
        "eligible": eligible,
        "heat_class": heat_class,
        "evidence": evidence,
        "rejection_reasons": [] if eligible else ["本周热度证据不足"],
    }
