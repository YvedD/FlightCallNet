#!/usr/bin/env python3
"""
Xeno-Canto API v3 ONLY
See: https://xeno-canto.org/explore/api
Do NOT use API v2 syntax.
"""

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
    python scripts/fetch_xc.py turdus_philomelos   # treat as species name under project root
"""

import sys
import os
import json
import time
import pathlib
import urllib.parse
import urllib.request
from pathlib import Path
import shutil
import argparse
import requests

XC_API_BASE = "https://xeno-canto.org/api/3/recordings"
API_KEY = "83480bce2ae2e6e988c3bd8fc79aea17161dc750"
REQUEST_DELAY = 1.2  # seconds between API calls


def fetch_recordings(species_name, species_type="flight", quality="A", max_per_species=50, per_page=50):
    recordings = []
    page = 1
    while len(recordings) < max_per_species:
        query = f'sp:"{species_name}"+grp:birds+type:"{species_type}"+q:{quality}'
        url = f"{XC_API_BASE}?query={query}&per_page={per_page}&page={page}&key={API_KEY}"
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            recs = data.get("recordings", [])
            if not recs:
                break
            for rec in recs:
                recordings.append(rec)
                if len(recordings) >= max_per_species:
                    break
            page += 1
        except Exception as e:
            print(f"Failed to fetch recordings for {species_name}: {e}")
            break
    print(f"Total recordings fetched for {species_name}: {len(recordings)}")
    return recordings


def choose_best_format(file_url: str) -> str:
    """Given a file URL (usually .mp3), try to find a .wav alternative on the same host.

    Strategy:
    - if file_url already endswith .wav, return it
    - otherwise, construct a candidate with .wav extension and perform a HEAD request
      to see if it's available (status_code 200). If yes, return the .wav URL.
    - otherwise return the original file_url
    """
    try:
        p = Path(file_url)
        if str(file_url).lower().endswith('.wav'):
            return file_url

        # Try replace extension with .wav
        wav_candidate = str(file_url).rsplit('.', 1)[0] + '.wav'
        # Use HEAD to check availability
        try:
            h = requests.head(wav_candidate, allow_redirects=True, timeout=5)
            if h.status_code == 200:
                return wav_candidate
        except Exception:
            pass

        # If not available, return original
        return file_url
    except Exception:
        return file_url


# ----------------- Project root helper -----------------
def find_project_root(config_filename: str = "species_config.json", max_up: int = 4) -> Path:
    """Zoek naar project root door te zoeken naar configbestand.

    Zoekt in:
      - huidige werkmap
      - map van dit script
      - oudermappen van het script (tot max_up niveaus)

    Retourneert Path van de map waar het configbestand staat of parent van dit script als fallback.
    """
    cwd = Path.cwd()
    cand = cwd / config_filename
    if cand.exists():
        return cwd

    script_dir = Path(__file__).resolve().parent
    cand = script_dir / config_filename
    if cand.exists():
        return script_dir

    p = script_dir
    for _ in range(max_up):
        p = p.parent
        cand = p / config_filename
        if cand.exists():
            return p

    # fallback
    return script_dir.parent


def main():
    parser = argparse.ArgumentParser(description='Fetch Xeno-canto recordings using species_config.json')
    parser.add_argument('species', nargs='?', default=None, help='Optional species name from species_config.json (e.g. "Anthus pratensis"). If omitted, process all species.')
    parser.add_argument('--project-root', '-p', dest='project_root', help='Force project root path (overrides env and auto-detect)')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Print planned actions and paths but do not download')
    args = parser.parse_args()

    # determine PROJECT_ROOT
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root).resolve()
        print(f"Using PROJECT_ROOT from --project-root: {PROJECT_ROOT}")
    else:
        env_root = os.environ.get('FLIGHTCALLNET_ROOT')
        if env_root:
            PROJECT_ROOT = Path(env_root).resolve()
            print(f"Using PROJECT_ROOT from FLIGHTCALLNET_ROOT: {PROJECT_ROOT}")
        else:
            PROJECT_ROOT = find_project_root()
            print(f"Using PROJECT_ROOT (auto-detected): {PROJECT_ROOT}")

    cfg_path = Path(PROJECT_ROOT) / 'species_config.json'
    if not cfg_path.exists():
        print(f"species_config.json niet gevonden in project root: {cfg_path}")
        return

    species_list = json.load(open(cfg_path, 'r', encoding='utf-8'))

    # select species to process
    to_process = []
    if args.species:
        # match by exact name or lowercase underscored
        name = args.species
        for s in species_list:
            if s.get('name') == name or s.get('name').lower() == name.lower() or s.get('name').lower().replace(' ', '_') == name.lower().replace(' ', '_'):
                to_process.append(s)
                break
        if not to_process:
            print(f"Soort '{name}' niet gevonden in species_config.json")
            return
    else:
        to_process = species_list

    for s in to_process:
        species_name = s['name']
        species_type = s.get('type', 'flight')
        quality = s.get('quality', 'A')
        max_per_species = s.get('max_per_species', 50)

        species_dirname = species_name.lower().replace(' ', '_')
        species_dir = Path(PROJECT_ROOT) / 'species' / species_dirname
        raw_dir = species_dir / 'raw'
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"Processing {species_name}: saving to {raw_dir.resolve()}")

        recordings = fetch_recordings(species_name, species_type, quality, max_per_species)
        if not recordings:
            print(f"No recordings found for {species_name}")
            continue

        for rec in recordings:
            file_url = rec.get('file') or rec.get('file')
            if not file_url:
                continue
            # Allow wav if available, else fallback to mp3
            chosen_url = choose_best_format(file_url)
            xc_id = rec.get('id')
            ext = Path(chosen_url).suffix or Path(file_url).suffix or '.mp3'
            dest = raw_dir / f"XC{xc_id}{ext}"
            if args.dry_run:
                print(f"Dry run: would download {chosen_url} -> {dest}")
                continue
            if dest.exists():
                print(f"Skipping existing {dest}")
                continue
            try:
                # ensure parent exists
                dest.parent.mkdir(parents=True, exist_ok=True)
                resp = requests.get(chosen_url, stream=True)
                resp.raise_for_status()
                with open(dest, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded -> {dest}")
            except Exception as e:
                print(f"Failed to download {chosen_url}: {e}")
            time.sleep(REQUEST_DELAY)

    print("Done.")


if __name__ == '__main__':
    main()
