# Audio Chunking Parameters Guide

## Overview

This document explains how to tune the audio chunking parameters in FlightCallNet to balance between capturing all relevant calls and avoiding excessive fragmentation of recordings.

## The Problem

When downloading and processing recordings from Xeno-Canto, audio files are split into individual "chunks" representing potential call events. If the chunking parameters are too sensitive, a single recording can generate hundreds of tiny fragments, many of which are just noise or brief pauses. If the parameters are too relaxed, you may miss individual calls or include too much silence.

## Key Parameters

The chunking behavior is controlled by three main parameters in `species_config.json`:

### 1. `min_silence_len` (milliseconds)

**What it does**: Defines the minimum duration of silence required to split the audio.

**Effect on chunking**:
- **Lower values (100-200ms)**: Splits on brief pauses, creates hundreds of chunks
- **Higher values (500-800ms)**: Only splits on clear gaps, creates fewer chunks
- **Recommended**: 500ms for flight calls

**Reasoning**: Flight calls often occur in sequences with brief natural pauses. A 500ms threshold ignores these pauses while still splitting on genuine silence between call bouts.

### 2. `silence_thresh` (dBFS)

**What it does**: Defines what volume level is considered "silence". Values are negative, with more negative = quieter.

**Effect on chunking**:
- **Higher values (-35 to -40 dBFS)**: More sensitive, treats quiet sounds as silence
- **Lower values (-50 to -55 dBFS)**: Less sensitive, only true silence triggers split
- **Recommended**: -50 dBFS

**Reasoning**: Many flight calls have quiet attack or decay phases. A threshold of -50 dBFS ensures these quiet parts aren't misidentified as silence, which would otherwise split a single call into multiple fragments.

### 3. `keep_silence` (milliseconds)

**What it does**: Amount of silence to preserve at the start and end of each chunk.

**Effect on chunks**:
- **0ms**: Chunks cut exactly at silence boundaries
- **100-300ms**: Chunks include context around the call
- **Recommended**: 200ms

**Reasoning**: Preserving context around calls helps classification algorithms recognize attack and decay characteristics. Since typical flight calls are 20-200ms, keeping 200ms of silence on each side provides important acoustic context.

## Default Configuration

The current defaults in `species_config.json` are:

```json
{
    "min_silence_len": 500,
    "silence_thresh": -50,
    "keep_silence": 200
}
```

These values significantly reduce chunk count compared to previous defaults (100ms / -40dB) while preserving call quality.

## Fine-Tuning Per Species

Different species may benefit from different settings:

### For species with very short, isolated calls:
```json
{
    "min_silence_len": 300,
    "silence_thresh": -50,
    "keep_silence": 150
}
```

### For species with longer call sequences:
```json
{
    "min_silence_len": 800,
    "silence_thresh": -55,
    "keep_silence": 250
}
```

### For noisy or poor-quality recordings:
```json
{
    "min_silence_len": 600,
    "silence_thresh": -45,
    "keep_silence": 200
}
```

## Testing Your Settings

After changing parameters:

1. Run the download script on a small sample (e.g., 5 recordings)
2. Check the `events/` directory to see how many chunks were created
3. Listen to a few chunks to verify quality
4. Adjust parameters and repeat if needed

Typical chunk counts per recording:
- **Too many (>50)**: Increase `min_silence_len` or lower `silence_thresh`
- **Too few (<5)**: Decrease `min_silence_len` or raise `silence_thresh`
- **About right (10-30)**: Parameters are well-tuned

## Additional Filters

Beyond chunking parameters, you can also control:

- `chunk_min_ms`: Minimum chunk duration (default: 150ms)
- `chunk_max_ms`: Maximum chunk duration (default: 1000ms)

These act as post-processing filters, discarding chunks that are too short (likely noise) or truncating chunks that are too long (likely not flight calls).

## Summary

The chunking parameters represent a trade-off between:
- **Recall**: Capturing all potential calls (favor lower thresholds)
- **Precision**: Avoiding noise and false fragments (favor higher thresholds)

For flight call detection, precision is generally preferred, as the subsequent classification step expects well-formed call segments.

Start with the recommended defaults and adjust based on your specific species and recording quality.
