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

