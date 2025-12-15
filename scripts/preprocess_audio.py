#!/usr/bin/env python3
"""
FlightCallNet – Audio preprocessing (v0.1)


- Converts audio to mono WAV
- Resamples to 22050 Hz
- Normalises amplitude
- Splits into manageable chunks
"""


import pathlib
import sys
import soundfile as sf
import numpy as np
import librosa


TARGET_SR = 22050
MAX_CHUNK_SEC = 10




def preprocess_file(src: pathlib.Path, dst_dir: pathlib.Path):
y, sr = librosa.load(src, sr=None, mono=True)
if sr != TARGET_SR:
y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)


if np.max(np.abs(y)) > 0:
y = y / np.max(np.abs(y))


samples_per_chunk = TARGET_SR * MAX_CHUNK_SEC
for i in range(0, len(y), samples_per_chunk):
chunk = y[i:i + samples_per_chunk]
if len(chunk) < TARGET_SR:
continue
out = dst_dir / f"{src.stem}_{i//samples_per_chunk}.wav"
sf.write(out, chunk, TARGET_SR)




def main():
if len(sys.argv) != 2:
print("Usage: preprocess_audio.py <species_dir>")
sys.exit(1)


species_dir = pathlib.Path(sys.argv[1])
raw_dir = species_dir / "samples" / "raw"
clean_dir = species_dir / "samples" / "clean"
clean_dir.mkdir(parents=True, exist_ok=True)


for wav in raw_dir.glob("*.wav"):
preprocess_file(wav, clean_dir)


print("Preprocessing complete.")




if __name__ == "__main__":
main()
