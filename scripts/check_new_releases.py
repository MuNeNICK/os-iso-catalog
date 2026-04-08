#!/usr/bin/env python3
"""Check for new OS releases via endoflife.date API.

Tracking rules are defined in data/images.yaml under the 'tracking' key.
No distro-specific logic lives in this script.
"""

import fnmatch
import json
import sys
from datetime import date
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "images.yaml"

EOL_API = "https://endoflife.date/api"
TIMEOUT = 15


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_catalog_versions(images, distro, match_depth):
    """Get set of normalized versions in our catalog for a distro."""
    versions = set()
    for img in images:
        if img.get("distro") != distro:
            continue
        v = str(img["version"])
        versions.add(v)  # Exact match
        parts = v.split(".")
        # Add all truncations down to match_depth
        for depth in range(1, len(parts) + 1):
            versions.add(".".join(parts[:depth]))
    return versions


def is_eol_past(eol_value):
    """Check if an EOL value indicates the release is already past EOL."""
    if eol_value is True:
        return True
    if isinstance(eol_value, str):
        try:
            return date.fromisoformat(eol_value) < date.today()
        except ValueError:
            pass
    return False


def matches_exclude(cycle, exclude_patterns):
    """Check if a cycle matches any exclude glob pattern."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(cycle, pattern):
            return True
    return False


def normalize_cycle(cycle, match_depth):
    """Normalize a cycle string to the configured match depth."""
    parts = cycle.split(".")
    return ".".join(parts[:match_depth])


def main():
    data = load_data()
    images = data.get("images", [])
    tracking = data.get("tracking", {})

    if not tracking:
        print("No tracking rules defined in images.yaml.")
        sys.exit(0)

    new_releases = []

    for distro, rules in tracking.items():
        product = rules.get("product")
        if not product:
            continue

        match_depth = rules.get("match_depth", 1)
        lts_only = rules.get("lts_only", False)
        exclude_cycles = rules.get("exclude_cycles", [])

        catalog_versions = get_catalog_versions(images, distro, match_depth)

        try:
            r = requests.get(f"{EOL_API}/{product}.json", timeout=TIMEOUT)
            if r.status_code != 200:
                print(f"  SKIP {distro}: API returned {r.status_code}")
                continue
            releases = r.json()
        except Exception as e:
            print(f"  SKIP {distro}: {e}")
            continue

        for rel in releases:
            eol = rel.get("eol", False)
            if is_eol_past(eol):
                continue

            cycle = str(rel.get("cycle", ""))
            if not cycle:
                continue

            # Apply exclude patterns
            if matches_exclude(cycle, exclude_cycles):
                continue

            # Apply LTS filter
            if lts_only and not rel.get("lts", False):
                continue

            # Normalize and check against catalog
            normalized = normalize_cycle(cycle, match_depth)
            if normalized not in catalog_versions and cycle not in catalog_versions:
                latest = rel.get("latest", cycle)
                new_releases.append({
                    "distro": distro,
                    "product": product,
                    "cycle": cycle,
                    "latest": latest,
                    "eol": eol,
                })

    if new_releases:
        print("New releases detected that are not in the catalog:\n")
        for nr in new_releases:
            print(f"  {nr['distro']} {nr['latest']} (cycle {nr['cycle']}, eol: {nr['eol']})")
        print(f"\nTotal: {len(new_releases)} new releases found.")
        print("\nAction: Add these to data/images.yaml with download URLs and checksums.")

        report_file = ROOT / "new-releases-report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(new_releases, f, indent=2, ensure_ascii=False)

        sys.exit(2)  # Signal new releases found
    else:
        print("No new releases detected. Catalog is up to date.")
        sys.exit(0)


if __name__ == "__main__":
    main()
