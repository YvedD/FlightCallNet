import os
import json
import requests
from pydub import AudioSegment
from pydub.silence import split_on_silence
import shutil

# ---------------- CONFIG ----------------
CONFIG_FILE = "species_config.json"  # JSON-bestand met soorten en instellingen
RAW_DIR = "raw"
EVENTS_DIR = "events"

# ---------------- HELPERS ----------------
def ensure_dirs(base_path):
    raw_path = os.path.join(base_path, RAW_DIR)
    events_path = os.path.join(base_path, EVENTS_DIR)
    os.makedirs(raw_path, exist_ok=True)
    os.makedirs(events_path, exist_ok=True)
    return raw_path, events_path

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
        with open(save_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        print(f"Downloaded {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def convert_to_wav(src_path, dst_path):
    audio = AudioSegment.from_file(src_path)
    audio.export(dst_path, format="wav")
    print(f"Converted {src_path} → {dst_path}")

def chunk_audio(wav_path, events_path, min_ms=150, max_ms=1000, silence_thresh=-40):
    audio = AudioSegment.from_wav(wav_path)
    chunks = split_on_silence(
        audio,
        min_silence_len=100,
        silence_thresh=silence_thresh
    )
    for i, chunk in enumerate(chunks):
        if len(chunk) < min_ms:
            continue
        if len(chunk) > max_ms:
            chunk = chunk[:max_ms]
        fname = os.path.join(events_path, f"{os.path.basename(wav_path)[:-4]}_chunk{i}.wav")
        chunk.export(fname, format="wav")
        print(f"Exported chunk: {fname}")

# ---------------- MAIN ----------------
def process_species(species_dict):
    species_name = species_dict["name"]
    species_type = species_dict.get("type", "flight")
    quality = species_dict.get("quality", "A")
    max_per_species = species_dict.get("max_per_species", 50)
    min_ms = species_dict.get("chunk_min_ms", 150)
    max_ms = species_dict.get("chunk_max_ms", 1000)
    silence_thresh = species_dict.get("silence_thresh", -40)

    print(f"\nProcessing species: {species_name} (type={species_type}, quality={quality})")
    base_path = os.path.join("species", species_name.lower().replace(" ", "_"))
    raw_path, events_path = ensure_dirs(base_path)

    recordings = fetch_recordings(species_name, species_type, quality, max_per_species)
    if not recordings:
        print(f"No recordings found for {species_name}")
        return

    for rec in recordings:
        xc_id = rec.get("id")
        mp3_url = rec.get("file")
        if not mp3_url:
            continue

        mp3_filename = os.path.join(raw_path, f"{xc_id}.mp3")
        wav_filename = os.path.join(raw_path, f"{xc_id}.wav")

        if not os.path.exists(mp3_filename):
            if not download_file(mp3_url, mp3_filename):
                continue
        if not os.path.exists(wav_filename):
            convert_to_wav(mp3_filename, wav_filename)

        chunk_audio(wav_filename, events_path, min_ms, max_ms, silence_thresh)

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} ontbreekt")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        species_list = json.load(f)

    for species_dict in species_list:
        process_species(species_dict)

if __name__ == "__main__":
    main()
