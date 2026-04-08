#!/usr/bin/env python3
"""Check EOL dates and auto-update status in data/images.yaml.

For distros with tracking rules, EOL dates are fetched from endoflife.date API.
For others, existing YAML dates are used as-is.
"""

import sys
from datetime import date
from pathlib import Path

import requests
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "images.yaml"

EOL_API = "https://endoflife.date/api"
TIMEOUT = 15


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


def fetch_eol_cycles(tracking):
    """Fetch EOL cycles from endoflife.date API for all tracked distros.

    Returns: {distro: [release_objects], ...}
    """
    result = {}
    for distro, rules in tracking.items():
        product = rules.get("product")
        if not product or not rules.get("eol_auto", True):
            continue
        try:
            r = requests.get(f"{EOL_API}/{product}.json", timeout=TIMEOUT)
            if r.status_code != 200:
                print(f"  WARN: {distro} API returned {r.status_code}",
                      file=sys.stderr)
                continue
            result[distro] = r.json()
        except Exception as e:
            print(f"  WARN: {distro}: {e}", file=sys.stderr)
    return result


def extract_eol_dates(rel):
    """Extract standard and extended EOL dates from an API release object.

    API field mapping:
    - extendedSupport (str) → extended  (Ubuntu, Debian)
    - support != eol (str)  → standard=support, extended=eol  (Rocky, Alma)
    - eol only (str)        → standard=eol  (Fedora, Alpine, OpenBSD, etc.)
    - eol is bool           → skip (no date available, e.g. NetBSD)
    """
    api_eol = rel.get("eol")
    api_support = rel.get("support")
    api_extended = rel.get("extendedSupport")

    standard = None
    extended = None

    if api_extended and isinstance(api_extended, str):
        if isinstance(api_eol, str):
            standard = api_eol
        extended = api_extended
    elif (api_support and isinstance(api_support, str)
          and api_eol and isinstance(api_eol, str)
          and api_support != api_eol):
        standard = api_support
        extended = api_eol
    elif isinstance(api_eol, str):
        standard = api_eol

    return standard, extended


def find_matching_cycle(version, releases, match_depth):
    """Find the API release that matches an image version."""
    parts = version.split(".")
    version_truncated = ".".join(parts[:match_depth])

    for rel in releases:
        cycle = str(rel.get("cycle", ""))
        if not cycle:
            continue

        if cycle == version:
            return rel

        cycle_parts = cycle.split(".")
        cycle_truncated = ".".join(cycle_parts[:match_depth])
        if version_truncated == cycle_truncated:
            return rel

    return None


def main():
    yaml = YAML()
    yaml.preserve_quotes = True

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    images = data.get("images", [])
    tracking = data.get("tracking", {})

    # Fetch EOL data from API for tracked distros
    print("Fetching EOL data from endoflife.date API...")
    api_cycles = fetch_eol_cycles(tracking)
    print(f"  Fetched data for {len(api_cycles)} distros.")

    date_changes = []
    status_changes = []

    for img in images:
        img_id = img["id"]
        distro = img.get("distro", "")
        version = str(img.get("version", ""))
        old_status = str(img["status"])
        eol_obj = img["eol"]

        # Update EOL dates from API if tracking is configured and eol_auto is not disabled
        if (distro in api_cycles and distro in tracking
                and tracking[distro].get("eol_auto", True)):
            match_depth = tracking[distro].get("match_depth", 1)
            rel = find_matching_cycle(
                version, api_cycles[distro], match_depth)

            if rel:
                new_std, new_ext = extract_eol_dates(rel)

                if new_std:
                    old_std = (str(eol_obj.get("standard"))
                               if eol_obj.get("standard") else None)
                    if old_std != new_std:
                        date_changes.append(
                            f"  {img_id}: standard {old_std} -> {new_std}")
                        eol_obj["standard"] = new_std

                if new_ext:
                    old_ext = (str(eol_obj.get("extended"))
                               if eol_obj.get("extended") else None)
                    if old_ext != new_ext:
                        date_changes.append(
                            f"  {img_id}: extended {old_ext} -> {new_ext}")
                        eol_obj["extended"] = new_ext

        # Compute status based on (possibly updated) EOL dates
        new_status = compute_status(eol_obj, old_status)
        if new_status != old_status:
            status_changes.append(
                f"  {img_id}: {old_status} -> {new_status}")
            img["status"] = new_status

    has_changes = bool(date_changes) or bool(status_changes)

    if date_changes:
        print(f"\nEOL date updates ({len(date_changes)}):")
        for c in date_changes:
            print(c)

    if status_changes:
        print(f"\nStatus changes ({len(status_changes)}):")
        for c in status_changes:
            print(c)

    if has_changes:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        print(f"\nUpdated {DATA_FILE}")
        sys.exit(2)  # Signal changes were made
    else:
        print("\nNo changes needed. EOL dates and statuses are up to date.")
        sys.exit(0)


if __name__ == "__main__":
    main()
