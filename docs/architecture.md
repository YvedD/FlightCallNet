# FlightCallNet – System Architecture

## Purpose

This document explains the **architectural and biological rationale** behind FlightCallNet. It clarifies how and why the system differs from existing bird sound recognition tools such as BirdNET or BirdNET-Pi.

FlightCallNet is explicitly designed for **flight calls and contact calls**, not for full song identification.

---

## Core biological assumptions

1. **Flight calls are short acoustic events**

   * Typically 20–200 ms
   * Often high-pitched, narrow-band
   * Low information density compared to song

2. **Flight/contact calls occur both day and night**

   * Nocturnal migration is important, but not exclusive
   * Many species (e.g. thrushes) use similar calls diurnally

3. **Species coverage must be regional**

   * A global species model is biologically weak
   * Users know which species are plausible

4. **False positives are unavoidable**

   * Wind, insects, bats, alarms, anthropogenic noise
   * Expert validation is part of the workflow

---

## Architectural overview

FlightCallNet uses a **layered pipeline** with strict separation of concerns:

```
Audio input (continuous)
   ↓
Acoustic event detector (fixed)
   ↓
Flight/contact call filter
   ↓
Embedding extraction
   ↓
Lightweight classifier (extensible)
   ↓
Logging & storage
```

Each layer has a clearly defined responsibility.

---

## Layer 1 – Audio capture

* Continuous or scheduled recording
* Low latency, low CPU usage
* Hardware-agnostic (USB mic / audio interface)

No assumptions are made about time of day.

---

## Layer 2 – Acoustic event detection (fixed)

**Question answered:**

> “Is there a short acoustic event worth analysing?”

Characteristics:

* High recall is preferred over high precision
* Species-agnostic
* Rarely retrained

This layer is conceptually similar to BirdVox-style detectors.

---

## Layer 3 – Flight/contact call filtering

**Question answered:**

> “Does this event resemble a flight/contact call?”

This step removes:

* Long tonal sounds
* Broadband noise bursts
* Clear song phrases

This layer is rule-based and/or lightly learned.

---

## Layer 4 – Embedding extraction

Validated events are transformed into:

* Fixed-length numeric representations (embeddings)
* Independent of species count

This enables:

* Fast classification
* Incremental retraining
* Model portability

---

## Layer 5 – Classification (extensible)

**Question answered:**

> “Which species or species group does this resemble?”

Key properties:

* Trained only on user-selected species
* Can be retrained locally on Raspberry Pi
* Supports species-level or group-level output

This is the **only layer** users extend.

---

## What FlightCallNet deliberately does NOT do

* Global species recognition
* Fully automatic retraining without validation
* Cloud-based inference
* Song identification

These choices are intentional and biological, not technical limitations.

---

## Comparison with BirdNET / BirdNET-Pi

| Aspect                  | BirdNET      | FlightCallNet        |
| ----------------------- | ------------ | -------------------- |
| Target sounds           | Song + calls | Flight/contact calls |
| Species scope           | Global       | Regional             |
| Night focus             | Partial      | None                 |
| Edge retraining         | No           | Yes                  |
| Human validation        | Optional     | Required             |
| Biological transparency | Low          | High                 |

FlightCallNet complements BirdNET; it does not compete with it.

---

## Design consequences

* Higher trust in detections
* Smaller, more accurate species sets
* Better suitability for migration monitoring

---

## Summary

FlightCallNet is a **biologically constrained, edge-first system** that prioritises interpretability and scientific usefulness over raw classification breadth.

