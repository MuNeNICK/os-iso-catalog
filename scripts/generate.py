#!/usr/bin/env python3
"""Generate JSON endpoints from data/images.yaml for GitHub Pages."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "images.yaml"
DOCS_DIR = ROOT / "docs" / "v1"

REQUIRED_FIELDS = {"id", "name", "category", "version", "arch", "status", "eol"}


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate(images):
    errors = []
    ids = set()
    for i, img in enumerate(images):
        for field in REQUIRED_FIELDS:
            if field not in img or img[field] is None:
                errors.append(f"Image #{i} ({img.get('id', '?')}): missing '{field}'")
        if "url" not in img and "download_page" not in img:
            errors.append(f"Image #{i} ({img.get('id', '?')}): needs 'url' or 'download_page'")
        img_id = img.get("id")
        if img_id in ids:
            errors.append(f"Duplicate id: {img_id}")
        ids.add(img_id)
    return errors


def make_envelope(images, generated_at, distros=None):
    envelope = {
        "meta": {
            "api_version": "v1",
            "generated_at": generated_at,
            "count": len(images),
        },
        "images": images,
    }
    if distros:
        envelope["distros"] = distros
    return envelope


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found", file=sys.stderr)
        sys.exit(1)

    data = load_data()
    images = data.get("images", [])
    distros = data.get("meta", {}).get("distros", {})

    errors = validate(images)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Collect unique architectures for dynamic arch filters
    arches = {img["arch"] for img in images}
    # Normalize arch names for filenames (amd64, arm64, x86_64, x64 etc.)
    arch_normalize = {
        "amd64": {"amd64", "x86_64", "x64"},
        "arm64": {"arm64", "aarch64"},
        "riscv64": {"riscv64"},
    }

    # Generate filtered endpoints
    filters = {
        "all.json": lambda _: True,
        "supported.json": lambda img: img["status"] in ("supported", "beta"),
        "eol.json": lambda img: img["status"] in ("eol", "eol-extended"),
        "linux.json": lambda img: img["category"] == "linux",
        "windows.json": lambda img: img["category"] == "windows",
        "bsd.json": lambda img: img["category"] == "bsd",
    }

    # Add arch-based filters dynamically
    for arch_key, arch_variants in arch_normalize.items():
        if arch_variants & arches:
            filters[f"{arch_key}.json"] = (
                lambda img, av=arch_variants: img["arch"] in av
            )

    for filename, predicate in filters.items():
        filtered = [img for img in images if predicate(img)]
        output = make_envelope(filtered, now, distros)
        write_json(DOCS_DIR / filename, output)
        print(f"  {filename}: {len(filtered)} images")

    print(f"\nGenerated {len(filters)} JSON files with {len(images)} total images.")


if __name__ == "__main__":
    main()
