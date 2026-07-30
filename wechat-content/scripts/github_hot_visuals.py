from __future__ import annotations

import json
import struct
from pathlib import Path


def select_theme(payload, families):
    categories = [str(item.get("category") or "") for item in payload.get("items") or []]
    family = (
        "ai_automation" if sum("ai" in value for value in categories) >= 3
        else "developer_tools" if sum(value in {"developer-tools", "terminal", "infrastructure"} for value in categories) >= 3
        else "creative_tools" if sum(value in {"design", "audio", "video"} for value in categories) >= 3
        else "systems_data" if sum(value in {"security", "data", "system"} for value in categories) >= 3
        else "mixed_default"
    )
    return {"family": family, **families[family]}


def png_size(path):
    try:
        with Path(path).open("rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            length = struct.unpack(">I", handle.read(4))[0]
            if handle.read(4) != b"IHDR" or length < 8:
                return None
            return struct.unpack(">II", handle.read(8))
    except OSError:
        return None


def valid_project_image(path, maximum_bytes):
    if not path or not Path(path).is_file() or Path(path).stat().st_size > maximum_bytes:
        return False
    size = png_size(path)
    return bool(size and size[0] >= 800 and size[1] >= 450)


def load_source_manifest(directory):
    if not directory:
        return {}
    path = Path(directory) / "source-manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def select_project_images(payload, project_image_dir, image_input_dir, image_mode, maximum_bytes):
    official_entries = (load_source_manifest(project_image_dir).get("images") or [])
    records = []
    for position, item in enumerate(payload.get("items") or [], 1):
        rank = int(item.get("rank") or position)
        repo = str(item.get("repo") or "")
        filename = f"projects/{rank:02d}.png"
        record = {
            "filename": f"项目-{position:02d}.png",
            "rank": rank,
            "repo": repo,
            "image_mode": "omitted",
            "source_path": "",
            "source_url": "",
            "is_real_interface": False,
            "license_status": "",
            "usage_status": "not_applicable",
            "verified_at": "",
            "human_confirmed": False,
            "fallback_reason": "",
        }
        approved_candidates = [
            value for value in item.get("visual_candidates") or []
            if value.get("usage_status") == "approved"
            and value.get("type") == "official_screenshot"
            and value.get("url")
        ]
        if image_mode in {"auto", "official-only"} and project_image_dir:
            entry = next(
                (
                    value for value in official_entries
                    if int(value.get("rank") or 0) == rank and value.get("repo") == repo
                ),
                None,
            )
            approved_urls = {
                value.get("url") for value in item.get("visual_candidates") or []
                if value.get("usage_status") == "approved"
                and value.get("type") == "official_screenshot"
            }
            official_path = Path(project_image_dir) / filename
            if (
                entry
                and entry.get("usage_status") == "approved"
                and entry.get("source_url") in approved_urls
                and valid_project_image(official_path, maximum_bytes)
            ):
                record.update(
                    image_mode="official_verified",
                    source_path=str(official_path),
                    source_url=str(entry.get("source_url") or ""),
                    is_real_interface=bool(entry.get("is_real_interface")),
                    license_status=str(entry.get("license_status") or ""),
                    usage_status="approved",
                    verified_at=str(entry.get("verified_at") or ""),
                    human_confirmed=bool(entry.get("human_confirmed")),
                )
        if (
            record["image_mode"] == "omitted"
            and image_mode in {"auto", "official-only"}
            and approved_candidates
        ):
            candidate = approved_candidates[0]
            record.update(
                image_mode="official_verified",
                source_url=str(candidate.get("url") or ""),
                is_real_interface=bool(candidate.get("is_real_interface")),
                license_status=str(candidate.get("license_status") or ""),
                usage_status="approved",
                verified_at=str(candidate.get("verified_at") or ""),
                human_confirmed=bool(candidate.get("human_confirmed")),
            )
        if (
            record["image_mode"] == "omitted"
            and image_mode in {"auto", "image2"}
            and image_input_dir
        ):
            generated_path = Path(image_input_dir) / filename
            if valid_project_image(generated_path, maximum_bytes):
                record.update(
                    image_mode="live_image2",
                    source_path=str(generated_path),
                    license_status="generated",
                    usage_status="generated",
                )
            else:
                record["fallback_reason"] = "image2_missing_or_invalid"
        if record["image_mode"] == "omitted" and not record["fallback_reason"]:
            record["fallback_reason"] = (
                "official_image_not_approved"
                if project_image_dir and image_mode in {"auto", "official-only"}
                else "no_usable_project_image"
            )
        records.append(record)
    return records


def select_article_images(project_images, image_input_dir, image_mode, maximum_bytes, minimum_project_or_topic_images=3):
    usable_project_count = sum(
        1 for record in project_images
        if record.get("image_mode") in {"official_verified", "live_image2"}
    )
    needed = max(0, minimum_project_or_topic_images - usable_project_count)
    records = []
    for index in range(1, needed + 1):
        filename = f"主题插图-{index:02d}.png"
        record = {
            "filename": filename,
            "rank": index,
            "image_mode": "local_theme_visual",
            "source_path": "",
            "usage_status": "generated_fallback",
            "fallback_reason": "project_images_below_minimum",
        }
        if image_mode in {"auto", "image2"} and image_input_dir:
            generated_path = Path(image_input_dir) / "articles" / f"{index:02d}.png"
            if valid_project_image(generated_path, maximum_bytes):
                record.update(
                    image_mode="live_image2",
                    source_path=str(generated_path),
                    usage_status="generated",
                    fallback_reason="",
                )
        records.append(record)
    return records
