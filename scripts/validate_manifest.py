#!/usr/bin/env python3
"""Validate manifest.json against the images in stickers/.

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
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HEX_RE = re.compile(r"^[a-f0-9]{64}$")


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

    disk_categories = sorted(
        path.name
        for path in STICKER_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if manifest.get("categories") != disk_categories:
        errors.append("categories 与 stickers/ 子目录不一致，请重新运行 build_manifest.py")

    listed_files: set[str] = set()
    seen_ids: set[str] = set()

    for index, item in enumerate(stickers):
        label = f"stickers[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象")
            continue

        sticker_id = item.get("id")
        if not isinstance(sticker_id, str) or not ID_RE.match(sticker_id):
            errors.append(f"{label}.id 不合法: {sticker_id!r}")
        elif sticker_id in seen_ids:
            errors.append(f"{label}.id 重复: {sticker_id}")
        else:
            seen_ids.add(sticker_id)

        for key in ("emotion", "description"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}.{key} 必须是非空字符串")

        tags = item.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            errors.append(f"{label}.tags 必须是字符串数组")

        usage = item.get("usage")
        if not isinstance(usage, str):
            errors.append(f"{label}.usage 必须是字符串")

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

    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in STICKER_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }
    for rel in sorted(actual_files - listed_files):
        errors.append(f"图片未写入清单，请运行 build_manifest.py: {rel}")

    base_url = manifest.get("base_url", "")
    if not isinstance(base_url, str) or "OWNER" in base_url or "REPO" in base_url:
        warnings.append("base_url 仍是占位符，建好仓库后请替换为实际地址")

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"校验失败: {len(errors)} 个错误")
        return 1

    print(f"校验通过: {len(stickers)} 张表情, {len(disk_categories)} 个分类")
    return 0


if __name__ == "__main__":
    sys.exit(main())
