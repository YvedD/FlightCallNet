#!/usr/bin/env python3
"""
FlightCallNet – Xeno-canto fetch script (v0.1)

This script downloads recordings from Xeno-canto based on a species
configuration directory containing an xc_query.yaml file.

Design goals:
- Simple, transparent behaviour
- No machine learning
- Safe defaults
- Reproducible downloads

Usage:
    python scripts/fetch_xc.py species/turdus_philomelos
"""

import sys
import json
import time
import pathlib
import urllib.parse
import urllib.request

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml")
    sys.exit(1)

XC_API_BASE = "https://xeno-canto.org/api/2/recordings"
USER_AGENT = "FlightCallNet/0.1 (research, non-commercial)"
REQUEST_DELAY = 1.2  # seconds between API calls


def load_yaml(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_query(cfg: dict) -> str:
    parts = []

    genus = cfg.get("genus")
    species = cfg.get("species")

    if genus:
        parts.append(f"gen:{genus}")
    if species:
        parts.append(f"sp:{species}")

    for kw in cfg.get("keywords", []):
        parts.append(kw)

    for ex in cfg.get("exclude", []):
        parts.append(f"-{ex}")

    min_q = cfg.get("min_quality")
    if min_q:
        parts.append(f"q:{min_q}")

    max_len = cfg.get("max_duration")
    if max_len:
        parts.append(f"len:<{max_len}")

    return " ".join(parts)


def fetch_page(query: str, page: int) -> dict:
    params = {
        "query": query,
        "page": page,
    }
    url = XC_API_BASE + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: pathlib.Path):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        out.write(resp.read())


def main():
    if len(sys.argv) != 2:
        print("Usage: fetch_xc.py <species_dir>")
        sys.exit(1)

    species_dir = pathlib.Path(sys.argv[1])
    if not species_dir.exists():
        print(f"Directory not found: {species_dir}")
        sys.exit(1)

    cfg_path = species_dir / "xc_query.yaml"
    if not cfg_path.exists():
        print("Missing xc_query.yaml")
        sys.exit(1)

    cfg = load_yaml(cfg_path)
    query = build_query(cfg)

    raw_dir = species_dir / "samples" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Xeno-canto query: {query}")

    page = 1
    downloaded = 0

    while True:
        data = fetch_page(query, page)
        recs = data.get("recordings", [])

        if not recs:
            break

        for rec in recs:
            file_url = rec.get("file")
            if not file_url:
                continue

            xc_id = rec.get("id")
            ext = pathlib.Path(file_url).suffix
            dest = raw_dir / f"XC{xc_id}{ext}"

            if dest.exists():
                continue

            try:
                print(f"Downloading XC{xc_id}")
                download_file(file_url, dest)
                downloaded += 1
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"Failed XC{xc_id}: {e}")

        if page >= int(data.get("numPages", 1)):
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    print(f"Done. Downloaded {downloaded} recordings.")


if __name__ == "__main__":
    main()
