#!/usr/bin/env python3
"""Check EOL dates and auto-update status in data/images.yaml."""

import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "images.yaml"


def parse_date(date_str):
    if date_str is None:
        return None
    try:
        return date.fromisoformat(str(date_str))
    except (ValueError, TypeError):
        return None


def compute_status(eol, current_status):
    """Compute the correct status based on EOL dates."""
    if current_status == "beta":
        return "beta"

    if eol.get("is_rolling", False):
        return "supported"

    standard = parse_date(eol.get("standard"))
    extended = parse_date(eol.get("extended"))
    today = date.today()

    if standard is None:
        return current_status  # Can't determine, keep as-is

    if today <= standard:
        return "supported"

    if extended is not None and today <= extended:
        return "eol-extended"

    return "eol"


def main():
    yaml = YAML()
    yaml.preserve_quotes = True

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    images = data.get("images", [])
    changes = []

    for img in images:
        img_id = img["id"]
        old_status = str(img["status"])
        new_status = compute_status(img["eol"], old_status)

        if new_status != old_status:
            changes.append((img_id, old_status, new_status))
            img["status"] = new_status

    if changes:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        print("EOL status changes detected:")
        for img_id, old, new in changes:
            print(f"  {img_id}: {old} -> {new}")
        sys.exit(2)  # Signal changes were made
    else:
        print("No EOL status changes.")
        sys.exit(0)


if __name__ == "__main__":
    main()
