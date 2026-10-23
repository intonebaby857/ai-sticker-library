#!/usr/bin/env python3
"""Validate manifest.json against the images in stickers/.

Every field except file facts is derived from the filename, so a mismatch
almost always means manifest.json is stale. Re-run build_manifest.py.

Usage:
    python3 scripts/validate_manifest.py
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
HEX_RE = re.compile(r"^[a-f0-9]{64}$")

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not MANIFEST.is_file():
        print("ERROR: 找不到 manifest.json")
        return 1

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: manifest.json 不是合法 JSON: {exc}")
        return 1

    for key in ("name", "version", "base_url", "categories", "stickers"):
        if key not in manifest:
            errors.append(f"缺少顶层字段: {key}")

    stickers = manifest.get("stickers")
    if not isinstance(stickers, list):
        errors.append("stickers 必须是数组")
        stickers = []

    categories = manifest.get("categories")
    if not isinstance(categories, list) or any(not isinstance(item, str) for item in categories):
        errors.append("categories 必须是字符串数组")
        categories = []

    listed_files: set[str] = set()
    seen_ids: set[str] = set()
    used_emotions: set[str] = set()

    for index, item in enumerate(stickers):
        label = f"stickers[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象")
            continue

        sticker_id = item.get("id")
        if not isinstance(sticker_id, str) or not NAME_RE.fullmatch(sticker_id):
            errors.append(
                f"{label}.id 必须是 心情-角色-动作 形式的小写短横线名: {sticker_id!r}"
            )
            continue
        if sticker_id in seen_ids:
            errors.append(f"{label}.id 重复: {sticker_id}")
        seen_ids.add(sticker_id)

        emotion = item.get("emotion")
        if not isinstance(emotion, str) or not emotion.strip():
            errors.append(f"{label}.emotion 必须是非空字符串")
        else:
            used_emotions.add(emotion)
            if emotion != sticker_id.split("-")[0]:
                errors.append(
                    f"{label}.emotion 应等于文件名的第一段 {sticker_id.split('-')[0]!r}: {emotion!r}"
                )

        tags = item.get("tags")
        if (
            not isinstance(tags, list)
            or not tags
            or any(not isinstance(tag, str) or not tag for tag in tags)
        ):
            errors.append(f"{label}.tags 必须是非空字符串数组")
        elif len(set(tags)) != len(tags):
            errors.append(f"{label}.tags 不能重复")

        if not isinstance(item.get("description"), str) or not item["description"].strip():
            errors.append(f"{label}.description 必须是非空字符串")
        if not isinstance(item.get("usage"), str) or not item["usage"].strip():
            errors.append(f"{label}.usage 必须是非空字符串")

        rel = item.get("file")
        if not isinstance(rel, str) or not rel.startswith("stickers/"):
            errors.append(f"{label}.file 必须以 stickers/ 开头: {rel!r}")
            continue
        listed_files.add(rel)

        path = ROOT / rel
        if path.suffix.lower() not in IMAGE_EXTS:
            errors.append(f"{label}.file 不是支持的图片格式: {rel}")
        if not path.is_file():
            errors.append(f"{label}.file 指向的文件不存在: {rel}")
            continue
        if path.stem != sticker_id:
            errors.append(f"{label}.file 的文件名应与 id 一致: {rel}")

        expected_format = path.suffix.lower().lstrip(".")
        if item.get("format") != expected_format:
            errors.append(f"{label}.format 应为 {expected_format}: {rel}")
        if item.get("bytes") != path.stat().st_size:
            errors.append(f"{label}.bytes 与文件大小不一致: {rel}")
        digest = item.get("sha256")
        if not isinstance(digest, str) or not HEX_RE.match(digest):
            errors.append(f"{label}.sha256 格式不合法: {rel}")
        elif digest != sha256(path):
            errors.append(f"{label}.sha256 与文件内容不一致: {rel}")

    expected_categories = sorted(set(KNOWN_EMOTIONS) | used_emotions)
    if isinstance(categories, list) and sorted(categories) != expected_categories:
        errors.append("categories 与心情列表不一致，请重新运行 build_manifest.py")

    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in STICKER_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }
    for rel in sorted(actual_files - listed_files):
        errors.append(f"图片未写入清单，请运行 build_manifest.py: {rel}")

    base_url = manifest.get("base_url", "")
    if not isinstance(base_url, str) or "OWNER" in base_url or "REPO" in base_url:
        warnings.append("base_url 仍是占位符，请替换为实际地址")

    image_base_url = manifest.get("image_base_url")
    if image_base_url is not None:
        if not isinstance(image_base_url, str) or not image_base_url.strip():
            errors.append("image_base_url 必须是非空字符串")
        elif not image_base_url.endswith("/"):
            warnings.append("image_base_url 建议以 / 结尾，方便和 file 拼接")

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"校验失败: {len(errors)} 个错误")
        return 1

    print(f"校验通过: {len(stickers)} 张表情, {len(expected_categories)} 个心情")
    return 0


if __name__ == "__main__":
    sys.exit(main())
