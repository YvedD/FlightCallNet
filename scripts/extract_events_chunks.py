# scripts/extract_events_chunks.py
"""
Xeno-Canto API v3 ONLY
See: https://xeno-canto.org/explore/api
Do NOT use API v2 syntax.
"""


import os
import librosa
import soundfile as sf
import numpy as np
from scipy.signal import butter, filtfilt

LOW = 2000
HIGH = 10000
MIN_EVENT_SEC = 0.15
MAX_EVENT_SEC = 1.0
SILENCE_THRESH = 0.02  # amplitude threshold
SILENCE_PAD = 0.05     # minimale stilte tussen events in sec

def bandpass_filter(y, sr):
    b, a = butter(4, [LOW / (sr / 2), HIGH / (sr / 2)], btype="band")
    return filtfilt(b, a, y)

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

        # amplitude > threshold
        above_thresh = np.where(np.abs(y_filt) > SILENCE_THRESH)[0]

        if len(above_thresh) == 0:
            continue

        # splits in events bij stiltes
        events = []
        start_idx = above_thresh[0]
        for i in range(1, len(above_thresh)):
            if (above_thresh[i] - above_thresh[i-1]) / sr > SILENCE_PAD:
                end_idx = above_thresh[i-1]
                events.append((start_idx, end_idx))
                start_idx = above_thresh[i]
        events.append((start_idx, above_thresh[-1]))

        # opslaan korte events
        for i, (start, end) in enumerate(events):
            dur = (end - start) / sr
            if MIN_EVENT_SEC <= dur <= MAX_EVENT_SEC:
                event_y = y_filt[start:end]
                base = os.path.splitext(filename)[0]
                out_file = os.path.join(events_dir, f"{base}_evt{i+1}.wav")
                sf.write(out_file, event_y, sr)
                print(f"Saved event: {out_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract_events_chunks.py <species_path>")
    else:
        extract_events_chunks(sys.argv[1])
