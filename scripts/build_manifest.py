#!/usr/bin/env python3
"""Build manifest.json from sticker filenames.

The filename is the metadata: emotion-character-action-detail.png
There are no sidecar files and no manual mapping table.

Usage:
    python3 scripts/build_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STICKER_DIR = ROOT / "stickers"
MANIFEST = ROOT / "manifest.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
STOPWORDS = {"a", "an", "the", "and", "of", "to", "in", "on", "at", "with", "under"}

KNOWN_EMOTIONS = [
    "angry",
    "celebrate",
    "confused",
    "happy",
    "love",
    "others",
    "sad",
    "surprised",
    "tired",
]

USAGE = {
    "happy": "用户开心、赞同或想庆祝时使用；语气轻松积极。",
    "sad": "用户难过、失落或需要安慰时使用；先共情，再发图。",
    "angry": "用户生气、吐槽或表达不满时使用；不要用来针对具体的人。",
    "surprised": "遇到意外、惊讶或剧情反转时使用。",
    "confused": "用户疑惑、没看懂或对话卡住时使用。",
    "love": "表达喜欢、爱意、撒娇或感谢时使用。",
    "tired": "用户累了、想躺平或准备收工时使用。",
    "celebrate": "完成目标、恭喜或庆祝时使用。",
    "others": "以上都不太合适、但气氛到位时使用。",
}
DEFAULT_USAGE = "当对话语境和文件名描述一致时使用。"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(image: Path) -> dict:
    rel = image.relative_to(ROOT).as_posix()
    stem = image.stem
    if not NAME_RE.fullmatch(stem):
        raise ValueError(
            f"文件名必须是 心情-角色-动作，全小写加短横线，例如 love-puppy-holding-big-heart.png: {rel}"
        )

    parts = stem.split("-")
    emotion = parts[0]
    tags = [part for part in dict.fromkeys(parts) if part not in STOPWORDS]

    return {
        "id": stem,
        "file": rel,
        "emotion": emotion,
        "tags": tags,
        "description": " ".join(parts[1:]),
        "usage": USAGE.get(emotion, DEFAULT_USAGE),
        "format": image.suffix.lower().lstrip("."),
        "bytes": image.stat().st_size,
        "sha256": sha256(image),
    }


def main() -> int:
    base: dict = {}
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as handle:
            base = json.load(handle)

    stickers: list[dict] = []
    problems: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    images = sorted(
        path
        for path in STICKER_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    )

    for image in images:
        try:
            item = describe(image)
        except ValueError as exc:
            problems.append(str(exc))
            continue

        if item["id"] in seen_ids:
            problems.append(f"id 重复: {item['id']} ({item['file']})")
            continue

        if item["emotion"] not in KNOWN_EMOTIONS:
            warnings.append(
                f"心情 {item['emotion']!r} 不在建议列表里: {item['file']} "
                f"（建议用 {', '.join(KNOWN_EMOTIONS)}）"
            )

        seen_ids.add(item["id"])
        stickers.append(item)

    categories = sorted(set(KNOWN_EMOTIONS) | {item["emotion"] for item in stickers})
    manifest = {
        "name": base.get("name", "AI Sticker Library"),
        "version": int(base.get("version", 1)),
        "description": base.get(
            "description",
            "A public, machine-readable sticker library for AI agents.",
        ),
        "base_url": base.get("base_url", ""),
        "categories": categories,
        "stickers": stickers,
    }

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"manifest.json 已更新: {len(stickers)} 张表情, {len(categories)} 个心情")
    for warning in warnings:
        print(f"WARN: {warning}")
    for problem in problems:
        print(f"ERROR: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
