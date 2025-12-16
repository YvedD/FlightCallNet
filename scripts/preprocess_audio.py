# scripts/preprocess_audio.py
"""
Xeno-Canto API v3 ONLY
See: https://xeno-canto.org/explore/api
Do NOT use API v2 syntax.
"""


import os
import librosa
import soundfile as sf

def preprocess_audio(species_path):
    raw_dir = os.path.join(species_path, "samples", "raw")
    clean_dir = os.path.join(species_path, "samples", "clean")
    os.makedirs(clean_dir, exist_ok=True)

    for filename in os.listdir(raw_dir):
        if filename.lower().endswith(".wav"):
            src = os.path.join(raw_dir, filename)
            y, sr = librosa.load(src, sr=None, mono=True)
            # normalisatie naar -1.0 tot 1.0
            y = y / max(abs(y))
            out_file = os.path.join(clean_dir, filename)
            sf.write(out_file, y, sr)
            print(f"Preprocessed: {out_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python preprocess_audio.py <species_path>")
    else:
        preprocess_audio(sys.argv[1])
