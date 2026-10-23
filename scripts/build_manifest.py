#!/usr/bin/env python3
"""Scan stickers/ and write manifest.json for AI consumption.

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
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sidecar(image: Path) -> dict:
    sidecar = image.with_name(image.name + ".json")
    if not sidecar.exists():
        return {}
    with sidecar.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"sidecar 必须是 JSON 对象: {sidecar.relative_to(ROOT)}")
    return data


def main() -> int:
    base: dict = {}
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as handle:
            base = json.load(handle)

    categories = sorted(
        path.name
        for path in STICKER_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )

    stickers = []
    problems = []
    seen_ids = set()

    for image in sorted(STICKER_DIR.rglob("*")):
        if not image.is_file() or image.suffix.lower() not in IMAGE_EXTS:
            continue

        rel = image.relative_to(ROOT).as_posix()
        sticker_id = image.stem

        if not ID_RE.match(sticker_id):
            problems.append(f"文件名不符合 id 规则（小写字母、数字、连字符）: {rel}")
            continue
        if sticker_id in seen_ids:
            problems.append(f"id 重复: {sticker_id} ({rel})")
            continue
        seen_ids.add(sticker_id)

        try:
            meta = load_sidecar(image)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            problems.append(f"元数据读取失败: {rel} ({exc})")
            meta = {}

        description = str(meta.get("description", "")).strip()
        if not description:
            problems.append(f"缺少 description: {image.name}.json")

        stickers.append(
            {
                "id": sticker_id,
                "file": rel,
                "emotion": str(meta.get("emotion") or image.parent.name),
                "tags": meta.get("tags", []),
                "description": description,
                "usage": str(meta.get("usage", "")),
                "format": image.suffix.lower().lstrip("."),
                "bytes": image.stat().st_size,
                "sha256": sha256(image),
            }
        )

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

    print(f"manifest.json 已更新: {len(stickers)} 张表情, {len(categories)} 个分类")
    for problem in problems:
        print(f"WARN: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
