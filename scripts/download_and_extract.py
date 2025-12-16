# scripts/download_and_extract.py
"""
Xeno-Canto API v3 ONLY
See: https://xeno-canto.org/explore/api
Do NOT use API v2 syntax.
"""


import os
import requests
import librosa
import soundfile as sf
import numpy as np
from scipy.signal import butter, filtfilt

LOW = 2000
HIGH = 10000
MIN_EVENT_SEC = 0.15
MAX_EVENT_SEC = 1.0
SILENCE_THRESH = 0.02
SILENCE_PAD = 0.05

def bandpass_filter(y, sr):
    b, a = butter(4, [LOW / (sr / 2), HIGH / (sr / 2)], btype="band")
    return filtfilt(b, a, y)

def make_dirs(species_path):
    for sub in ["raw", "clean", "events"]:
        os.makedirs(os.path.join(species_path, "samples", sub), exist_ok=True)

def download_xc(species_name, species_path, max_records=20):
    """
    Download audio from Xeno-canto API (first max_records recordings)
    """
    raw_dir = os.path.join(species_path, "samples", "raw")
    base_url = "https://www.xeno-canto.org/api/2/recordings"
    query = f"?query={species_name}"
    response = requests.get(base_url + query)
    if response.status_code != 200:
        print(f"Failed to fetch {species_name} from Xeno-canto")
        return
    data = response.json()
    recordings = data.get("recordings", [])[:max_records]
    for rec in recordings:
        file_url = f"https:{rec['file']}" if rec['file'].startswith("//") else rec['file']
        filename = os.path.join(raw_dir, os.path.basename(file_url))
        if os.path.exists(filename):
            continue
        print(f"Downloading {filename}")
        try:
            r = requests.get(file_url)
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print(f"Error downloading {file_url}: {e}")

def extract_events_chunks(species_path):
    raw_dir = os.path.join(species_path, "samples", "raw")
    events_dir = os.path.join(species_path, "samples", "events")
    os.makedirs(events_dir, exist_ok=True)

    for filename in os.listdir(raw_dir):
        if not (filename.lower().endswith(".wav") or filename.lower().endswith(".mp3")):
            continue

        src = os.path.join(raw_dir, filename)
        y, sr = librosa.load(src, sr=None, mono=True)
        y_filt = bandpass_filter(y, sr)

        # splits bij stiltes
        above_thresh = np.where(np.abs(y_filt) > SILENCE_THRESH)[0]
        if len(above_thresh) == 0:
            continue

        events = []
        start_idx = above_thresh[0]
        for i in range(1, len(above_thresh)):
            if (above_thresh[i] - above_thresh[i-1]) / sr > SILENCE_PAD:
                end_idx = above_thresh[i-1]
                events.append((start_idx, end_idx))
                start_idx = above_thresh[i]
        events.append((start_idx, above_thresh[-1]))

        for i, (start, end) in enumerate(events):
            dur = (end - start) / sr
            if MIN_EVENT_SEC <= dur <= MAX_EVENT_SEC:
                event_y = y_filt[start:end]
                base = os.path.splitext(filename)[0]
                out_file = os.path.join(events_dir, f"{base}_evt{i+1}.wav")
                sf.write(out_file, event_y, sr)
                print(f"Saved event: {out_file}")

def process_species(species_name):
    species_path = os.path.join("species", species_name)
    make_dirs(species_path)
    download_xc(species_name, species_path)
    extract_events_chunks(species_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python download_and_extract.py <species1> [species2 ...]")
    else:
        for sp in sys.argv[1:]:
            print(f"Processing species: {sp}")
            process_species(sp)
