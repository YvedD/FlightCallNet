"""
Xeno-Canto API v3 ONLY
See: https://xeno-canto.org/explore/api
Do NOT use API v2 syntax.
"""


import os
import json
import requests
from pydub import AudioSegment
from pydub.silence import split_on_silence
import shutil
from pathlib import Path
import argparse
import concurrent.futures
import math

try:
    from utils_audio import convert_to_mono_wav
except Exception:
    # fallback if import fails (scripts run with different cwd); try import by script dir
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location('utils_audio', Path(__file__).resolve().parent / 'utils_audio.py')
    utils_audio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_audio)
    convert_to_mono_wav = utils_audio.convert_to_mono_wav

# ---------------- CONFIG ----------------
# CONFIG_FILE kan nu automatisch gevonden worden in meerdere locaties.
DEFAULT_CONFIG_FILENAME = "species_config.json"


def find_config_path(filename: str) -> str:
    """Zoekt naar het configuratiebestand op nuttige locaties en geeft het absolute pad terug.

    Volgorde van zoeken:
    - huidige werkmap (os.getcwd())
    - map van dit script
    - oudermappen van het script (tot 4 niveaus omhoog)

    Als het bestand niet gevonden wordt, retourneert de originele bestandsnaam (zodat
    bestaande foutafhandeling in main() nog steeds werkt).
    """
    cwd = Path.cwd()
    tried = []

    # 1) huidige werkmap
    candidate = cwd / filename
    tried.append(str(candidate))
    if candidate.exists():
        print(f"Found config in current working directory: {candidate}")
        return str(candidate)

    # 2) map van dit script
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir / filename
    tried.append(str(candidate))
    if candidate.exists():
        print(f"Found config in script directory: {candidate}")
        return str(candidate)

    # 3) oudermappen van het script (max 4 niveaus)
    p = script_dir
    for _ in range(4):
        p = p.parent
        candidate = p / filename
        tried.append(str(candidate))
        if candidate.exists():
            print(f"Found config in parent directory: {candidate}")
            return str(candidate)

    # Niet gevonden
    print("Config file not found in these locations:")
    for t in tried:
        print(f"  - {t}")
    print(f"Current working directory: {cwd}")
    # Geef fallback (originele bestandsnaam) terug, zodat bestaande check in main nog steeds faalt
    return filename

# Zet CONFIG_FILE op het gevonden pad (of de fallback naam)
CONFIG_FILE = find_config_path(DEFAULT_CONFIG_FILENAME)  # JSON-bestand met soorten en instellingen
# Resolveer CONFIG_FILE naar een absoluut pad wanneer mogelijk
if os.path.isabs(CONFIG_FILE) and os.path.exists(CONFIG_FILE):
    CONFIG_FILE = str(Path(CONFIG_FILE).resolve())

RAW_DIR = "raw"
EVENTS_DIR = "events"

# Bepaal gedetecteerde project root (wordt overschreven in main als CLI/env opgegeven wordt)
if os.path.isabs(CONFIG_FILE) and os.path.exists(CONFIG_FILE):
    _DETECTED_PROJECT_ROOT = Path(CONFIG_FILE).resolve().parent
else:
    _DETECTED_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Initiele waarde (kan overschreven worden in main)
PROJECT_ROOT = _DETECTED_PROJECT_ROOT

print(f"(detected) PROJECT_ROOT: {_DETECTED_PROJECT_ROOT}")

# ---------------- CHUNKING PARAMETERS GUIDE ----------------
# The chunking parameters control how audio files are split into individual call events.
# Adjust these to balance between:
#   - Too many chunks: hundreds of tiny fragments, including noise
#   - Too few chunks: missing individual calls or including too much silence
#
# Key parameters:
#   - min_silence_len (ms): Minimum silence duration to split on
#     * Lower values (100-200ms): Split on brief pauses, may create hundreds of chunks
#     * Higher values (500-800ms): Only split on clear gaps, fewer chunks
#     * Recommended: 500ms for flight calls (ignores natural pauses within call sequences)
#
#   - silence_thresh (dBFS): Volume level considered as "silence"
#     * Higher values (-35 to -40 dBFS): More sensitive, treats quiet sounds as silence
#     * Lower values (-50 to -55 dBFS): Less sensitive, only true silence triggers split
#     * Recommended: -50 dBFS (avoids splitting during quiet parts of calls)
#
#   - keep_silence (ms): Amount of silence to preserve around chunks
#     * 0ms: Cut chunks exactly at silence boundaries
#     * 100-300ms: Keep context around calls for better classification
#     * Recommended: 200ms (preserves attack/decay characteristics)
#

# ---------------- HELPERS ----------------
def ensure_dirs(base_path):
    """Maak (absolute) `raw` en `events` directories onder `base_path` en geef hun paden terug.

    base_path kan een string of Path zijn. Functie zorgt voor absolute paden en print waar
    de directories zijn aangemaakt (handig voor debugging wanneer cwd anders is).
    """
    base = Path(base_path)
    raw_path = base / RAW_DIR
    events_path = base / EVENTS_DIR
    raw_path.mkdir(parents=True, exist_ok=True)
    events_path.mkdir(parents=True, exist_ok=True)
    print(f"Ensured directories:\n  raw: {raw_path}\n  events: {events_path}")
    return str(raw_path), str(events_path)

def fetch_recordings(species_name, species_type="flight", quality="A", max_per_species=50, per_page=50):
    """
    Haal recordings op van Xeno-Canto v3 API voor een soort.
    """
    API_KEY = "83480bce2ae2e6e988c3bd8fc79aea17161dc750"
    recordings = []
    page = 1
    while len(recordings) < max_per_species:
        query = f'sp:"{species_name}"+grp:birds+type:"{species_type}"+q:{quality}'
        url = f"https://xeno-canto.org/api/3/recordings?query={query}&per_page={per_page}&page={page}&key={API_KEY}"
        print(f"Fetching page {page} for {species_name}")
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
            print(f"Failed to fetch recordings: {e}")
            break
    print(f"Total recordings fetched for {species_name}: {len(recordings)}")
    return recordings

def download_file(url, save_path):
    try:
        if url.startswith("//"):
            url = "https:" + url
        r = requests.get(url, stream=True)
        r.raise_for_status()
        save_p = Path(save_path)
        save_p.parent.mkdir(parents=True, exist_ok=True)
        with open(save_p, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        print(f"Downloaded to: {save_p.resolve()}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def convert_to_wav(src_path, dst_path):
    """Convert source audio to mono WAV using utils_audio (ffmpeg preferred)."""
    dst = Path(dst_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ok = convert_to_mono_wav(src_path, dst, sample_rate=44100, channels=1, overwrite=False)
    if ok:
        print(f"Converted {src_path} → {dst.resolve()}")
    else:
        print(f"Conversion failed for {src_path} -> {dst}")

def chunk_audio(wav_path, events_path, min_ms=150, max_ms=1000, silence_thresh=-50, min_silence_len=500, keep_silence=200):
    """
    Chunk audio by splitting on silence periods.

    Parameters:
    - min_ms: Minimum chunk duration in milliseconds (default: 150)
    - max_ms: Maximum chunk duration in milliseconds (default: 1000)
    - silence_thresh: Silence threshold in dBFS (default: -50). Lower = less sensitive
    - min_silence_len: Minimum silence duration to split on, in ms (default: 500)
                        Increased from 100ms to avoid splitting on brief natural pauses
    - keep_silence: Amount of silence to keep at start/end of chunks, in ms (default: 200)
                     Preserves context around calls for better classification
    """
    audio = AudioSegment.from_wav(wav_path)
    chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence
    )

    exported_count = 0
    for i, chunk in enumerate(chunks):
        if len(chunk) < min_ms:
            continue
        if len(chunk) > max_ms:
            chunk = chunk[:max_ms]
        fname = Path(events_path) / f"{Path(wav_path).stem}_chunk{i}.wav"
        fname.parent.mkdir(parents=True, exist_ok=True)
        chunk.export(str(fname), format="wav")
        exported_count += 1

    print(f"Exported {exported_count} chunks from {Path(wav_path).name} into {Path(events_path).resolve()}")

# ---------------- MAIN ----------------
def process_species(species_dict, dry_run=False, workers_override=None):
    species_name = species_dict["name"]
    species_type = species_dict.get("type", "flight")
    quality = species_dict.get("quality", "A")
    max_per_species = species_dict.get("max_per_species", 50)
    min_ms = species_dict.get("chunk_min_ms", 150)
    max_ms = species_dict.get("chunk_max_ms", 1000)
    silence_thresh = species_dict.get("silence_thresh", -50)  # Changed default from -40 to -50 (less sensitive)
    min_silence_len = species_dict.get("min_silence_len", 500)  # Increased from 100 to 500ms
    keep_silence = species_dict.get("keep_silence", 200)  # Keep 200ms of silence around chunks

    print(f"\nProcessing species: {species_name} (type={species_type}, quality={quality})")
    # Zorg dat de species directories altijd onder PROJECT_ROOT worden aangemaakt
    species_dirname = species_name.lower().replace(" ", "_")
    base_path = Path(PROJECT_ROOT) / "species" / species_dirname
    print(f"Using base_path for species: {base_path}")
    raw_path, events_path = ensure_dirs(base_path)

    recordings = fetch_recordings(species_name, species_type, quality, max_per_species)
    if not recordings:
        print(f"No recordings found for {species_name}")
        return

    # Determine number of workers: allow override from species config or use sensible default
    cfg_workers = species_dict.get('workers')
    if cfg_workers is not None:
        try:
            workers = int(cfg_workers)
        except Exception:
            workers = None
    else:
        workers = None

    # Override with global CLI option if provided
    if workers_override is not None:
        workers = workers_override

    # default: min(4, cpu_count or 2)
    if workers is None:
        try:
            cpu = os.cpu_count() or 2
        except Exception:
            cpu = 2
        workers = min(4, max(1, cpu))

    print(f"Processing {len(recordings)} recordings for {species_name} with {workers} workers")

    def handle_recording(rec):
        xc_id = rec.get('id')
        file_url = rec.get('file')
        if not file_url:
            return (xc_id, False, 'no file url')

        mp3_path = Path(raw_path) / f"XC{xc_id}.mp3"
        wav_path = Path(raw_path) / f"XC{xc_id}.wav"

        if dry_run:
            print(f"Dry run: would download {file_url} -> {mp3_path}")
            print(f"Dry run: would convert -> {wav_path}")
            print(f"Dry run: would chunk {wav_path} -> {events_path}")
            return (xc_id, True, 'dry-run')

        # Download if needed
        if not mp3_path.exists() and not wav_path.exists():
            ok = download_file(file_url, str(mp3_path))
            if not ok:
                return (xc_id, False, 'download failed')

        # If wav not exists, convert MP3 -> WAV (force mono)
        if not wav_path.exists():
            src_for_convert = str(mp3_path) if mp3_path.exists() else str(wav_path)
            convert_to_wav(src_for_convert, str(wav_path))

        # Chunk
        try:
            chunk_audio(str(wav_path), str(events_path), min_ms, max_ms, silence_thresh, min_silence_len, keep_silence)
            return (xc_id, True, 'ok')
        except Exception as e:
            return (xc_id, False, f'chunk error: {e}')

    # Run in a thread pool (safer cross-platform and avoids heavy pickling)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(handle_recording, rec): rec for rec in recordings}
        for fut in concurrent.futures.as_completed(futures):
            rec = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"Recording processing failed: {e}")
                results.append((None, False, str(e)))
            else:
                results.append(res)

    # Summary
    success = sum(1 for r in results if r[1])
    print(f"Finished species {species_name}: {success}/{len(recordings)} succeeded")

def main():
    parser = argparse.ArgumentParser(description='Download and chunk Xeno-canto recordings from species_config.json')
    parser.add_argument('--project-root', '-p', dest='project_root', help='Force project root path (overrides env and auto-detect)')
    parser.add_argument('--workers', type=int, dest='workers', help='Override number of parallel workers per species')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Print planned actions and paths but do not download/convert')
    args = parser.parse_args()

    # Bepaal final PROJECT_ROOT: prioriteit CLI > env var > gedetecteerd
    global PROJECT_ROOT, CONFIG_FILE
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root).resolve()
        print(f"Using PROJECT_ROOT from --project-root: {PROJECT_ROOT}")
        # probeer config in deze root
        candidate = PROJECT_ROOT / DEFAULT_CONFIG_FILENAME
        if candidate.exists():
            CONFIG_FILE = str(candidate)
        else:
            print(f"Warning: {candidate} niet gevonden; gebruik bestaande CONFIG_FILE: {CONFIG_FILE}")
    else:
        env_root = os.environ.get('FLIGHTCALLNET_ROOT')
        if env_root:
            PROJECT_ROOT = Path(env_root).resolve()
            print(f"Using PROJECT_ROOT from FLIGHTCALLNET_ROOT: {PROJECT_ROOT}")
        else:
            PROJECT_ROOT = _DETECTED_PROJECT_ROOT
            print(f"Using PROJECT_ROOT (auto-detected): {PROJECT_ROOT}")

    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} ontbreekt")
        return

    print(f"Using config file: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        species_list = json.load(f)

    for species_dict in species_list:
        process_species(species_dict, dry_run=args.dry_run, workers_override=args.workers)


if __name__ == "__main__":
    main()
