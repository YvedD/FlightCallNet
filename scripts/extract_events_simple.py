#!/usr/bin/env python3
"""
FlightCallNet – Simple event extraction (v0.1)


Energy-based + band-limited test detector.
THIS IS TEMPORARY TEST CODE.
"""


import pathlib
import sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter


SR = 22050
LOW = 2500
HIGH = 9000
THRESHOLD = 0.02
EVENT_MIN_SAMPLES = int(0.02 * SR)
EVENT_MAX_SAMPLES = int(0.3 * SR)




def bandpass(data):
b, a = butter(4, [LOW / (SR / 2), HIGH / (SR / 2)], btype="band")
return lfilter(b, a, data)




def extract_events(wav, out_dir):
y, sr = sf.read(wav)
y = bandpass(y)
energy = np.abs(y)


active = energy > THRESHOLD
start = None


for i, val in enumerate(active):
if val and start is None:
start = i
elif not val and start is not None:
length = i - start
if EVENT_MIN_SAMPLES <= length <= EVENT_MAX_SAMPLES:
out = y[start:i]
out_path = out_dir / f"{wav.stem}_{start}.wav"
sf.write(out_path, out, SR)
start = None




def main():
if len(sys.argv) != 2:
print("Usage: extract_events_simple.py <species_dir>")
sys.exit(1)


species_dir = pathlib.Path(sys.argv[1])
clean_dir = species_dir / "samples" / "clean"
event_dir = species_dir / "samples" / "events"
event_dir.mkdir(parents=True, exist_ok=True)


for wav in clean_dir.glob("*.wav"):
extract_events(wav, event_dir)


print("Event extraction complete.")




if __name__ == "__main__":
main()
