# FlightCallNet

**FlightCallNet** is an open-source, edge-first bioacoustic system for detecting and classifying avian flight calls and contact calls. It is designed for long-term monitoring of bird movement and migration, running entirely on low-power hardware such as a Raspberry Pi.

Unlike general bird song recognisers, FlightCallNet focuses on **short, non-song vocal events** (flight calls, contact calls) that occur both during the day and at night. The system is biologically informed, regionally adaptable, and transparent by design.

---

## Project goals

* Detect short avian acoustic events relevant to flight and movement
* Distinguish flight/contact calls from song and background noise
* Support region-specific species sets (e.g. migrants, local specialties)
* Run fully offline on edge devices (Raspberry Pi 4 recommended)
* Allow users to extend the system with new species in a controlled way

FlightCallNet is **not** a general bird song identification app and does not aim to identify every vocalisation to species level. Its primary goal is **reliable event detection and biologically meaningful classification**.

---

## Conceptual architecture

```
Microphone (24/7)
   ↓
Acoustic event detection
   ↓
Flight/contact call filtering
   ↓
Classification (group or species)
   ↓
Logging + audio storage
```

Key principles:

* Always-on listening (no night-only assumption)
* Event-based processing (short audio snippets)
* Fixed detection layer, extensible classification layer
* Human-in-the-loop for species expansion

---

## Hardware requirements

* Raspberry Pi 4 (4 GB minimum, 8 GB recommended)
* Raspberry Pi OS 64-bit
* USB audio interface or USB microphone
* Sufficient storage for audio snippets (USB SSD recommended)

---

## Software stack (planned)

* Python 3.10+
* NumPy / SciPy
* Audio I/O (ALSA, sounddevice or arecord-based capture)
* Spectral analysis (librosa or equivalent)
* Pretrained acoustic event detector (BirdVox-style)
* Lightweight classifier (embedding-based)

No cloud services are required.

---

## Repository structure

```
FlightCallNet/
├─ README.md
├─ docs/
│  ├─ adding_species.md
│  ├─ architecture.md
│  └─ roadmap.md
├─ fcnet/
│  ├─ __init__.py
│  ├─ audio/
│  ├─ detection/
│  ├─ classification/
│  ├─ training/
│  └─ utils/
├─ species/
│  ├─ example_species/
│  │  ├─ metadata.yaml
│  │  ├─ xc_query.yaml
│  │  └─ samples/
│  └─ README.md
├─ scripts/
│  ├─ fetch_xc.py
│  ├─ preprocess_audio.py
│  ├─ extract_events.py
│  └─ retrain_classifier.py
├─ data/
│  ├─ raw_audio/
│  ├─ events/
│  └─ models/
└─ LICENSE
```

---

## Current status

FlightCallNet is in an early design and prototyping phase (v0.1).

At this stage:

* The biological and architectural concepts are defined
* The repository structure is stabilised
* Initial tooling for species expansion is being designed

Expect rapid changes.

---

## Intended audience

* Migration researchers and bird observatories
* Advanced birders and citizen scientists
* Developers working on bioacoustic edge systems

A background in ornithology is more important than a background in machine learning.

---

## License

To be determined (likely MIT or GPL-3, depending on included components).

---

## Disclaimer

FlightCallNet provides probabilistic detections and classifications. All results must be interpreted with biological expertise. The system does not replace expert validation.


# Adding species to FlightCallNet

This document explains how users can extend FlightCallNet with **new species or call types**, using openly available recordings (e.g. Xeno-canto) while keeping the system biologically and technically stable.

The workflow is designed for **non-IT users**, with minimal manual intervention and strong defaults.

---

## Design philosophy

* Species are added **incrementally**, not all at once
* New species do not retrain the full detection system
* Retraining affects **only the classification layer**
* Human validation remains essential

FlightCallNet separates:

* *"Is there a flight/contact call?"* (fixed detector)
* *"Which species/group does it resemble?"* (extensible classifier)

---

## Species definition

Each species lives in its own directory under `species/`:

```
species/
└─ turdus_philomelos/
   ├─ metadata.yaml
   ├─ xc_query.yaml
   └─ samples/
```

### metadata.yaml

Contains biological and practical constraints:

```yaml
scientific_name: Turdus philomelos
common_name: Song Thrush
call_types:
  - flight_call
  - contact_call
region:
  - Western Europe
confidence_target: species
notes: "Short high-pitched tseep, day and night"
```

### xc_query.yaml

Defines how recordings are fetched from Xeno-canto:

```yaml
genus: Turdus
species: philomelos
keywords:
  - flight
  - call
exclude:
  - song
min_quality: B
max_duration: 10
```

This file is used by an automated fetch script.

---

## Step-by-step workflow

### 1. Fetch recordings

Run:

```
python scripts/fetch_xc.py species/turdus_philomelos
```

This script:

* Queries Xeno-canto
* Downloads matching recordings
* Stores them under `samples/raw/`

---

### 2. Preprocess audio

```
python scripts/preprocess_audio.py species/turdus_philomelos
```

This step:

* Resamples audio
* Normalises levels
* Splits long recordings
* Discards low SNR segments

Output is stored in `samples/clean/`.

---

### 3. Extract candidate events

```
python scripts/extract_events.py species/turdus_philomelos
```

This uses the fixed flight-call detector to:

* Identify short acoustic events
* Save them as individual snippets

False positives are expected.

---

### 4. Human validation (required)

Before retraining:

* Listen to extracted snippets
* Delete obvious non-target sounds
* Optionally label subtypes (e.g. alarm vs contact)

FlightCallNet intentionally **does not automate this step**.

---

### 5. Retrain classifier

```
python scripts/retrain_classifier.py
```

This step:

* Extracts embeddings from all validated snippets
* Updates the classification model
* Saves a new lightweight model under `data/models/`

Retraining typically takes minutes on a Raspberry Pi.

---

## What is *not* retrained

* The acoustic event detector
* The notion of "flight call"
* The entire species universe

This ensures system stability.

---

## Practical recommendations

* Start with 2–5 species only
* Prefer many short calls over few long recordings
* Use conservative XC filters
* Document biological assumptions in `metadata.yaml`

---

## Legal and ethical note

Users are responsible for complying with Xeno-canto’s license terms. Attribution should be preserved where required.

---

## Summary

FlightCallNet allows controlled, biologically meaningful expansion without requiring machine learning expertise, while avoiding uncontrolled model drift.

