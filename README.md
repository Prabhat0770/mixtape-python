# Studio DJ Mixtape & YouTube Video Production Engine

A pro-grade Python DSP engine and multi-tab Streamlit Studio that sequences, normalizes, and mixes multiple audio tracks into seamless mixtapes with DJ transition curves, generates timestamped YouTube descriptions & CUE sheets, and renders dynamic waveform-overlay MP4 videos ready for publication.

---

## Key Capabilities & DSP Upgrades

### 1. Studio Audio DSP Engine (`src/mixer.py` & `src/audio_inspector.py`)
- **Silence Trimming**: Automatically detects and strips leading/trailing silence (`pydub.silence.detect_leading_silence`) from each track before mixing to prevent dead air.
- **Loudness Normalization**: Targets standard YouTube loudness (`-14.0 dBFS` by default) with peak headroom limiting to prevent digital clipping.
- **BPM & Energy Analysis**: Extracts tempo (BPM) and RMS energy using `librosa` (with clean fallback), powering a **Smart Harmonic/BPM Sort** mode that smoothly builds tempo and energy across the mixtape.
- **3 Studio Crossfade Curves**:
  - `Constant-Power Crossfade`: Mathematically exact sine/cosine gain curves eliminating the mid-transition 3dB volume dip.
  - `EQ Filter Swap (Low-Pass/High-Pass)`: Classic DJ transition rolling off high/mid presence on the outgoing track while high-pass filtering the incoming track.
  - `Club Bass-Swap`: Splits tracks at 250 Hz, crossfading mid/high frequencies smoothly while swapping basslines decisively at the midpoint ($T/2$).

### 2. Cover Art Studio & Dynamic FFmpeg Visualizer (`src/video_generator.py`)
- **Cover Art Studio**: Center-crops and scales any aspect ratio to 720p or 1080p, featuring an optional blurred background fill and a sleek glassmorphic semi-transparent typography badge showing the Mixtape Title and Genre.
- **Dynamic Waveform Visualizer**: Optional live audio spectrum overlay composited over the cover art using FFmpeg's `showwaves` filter while maintaining `-preset ultrafast` and `-pix_fmt yuv420p` for rapid encoding.

### 3. YouTube SEO & CUE Sheet Engine (`src/description_generator.py`)
- **BPM-Enriched Timestamps**: Generates copy-ready tracklists with detected BPM annotations (e.g. `00:00 - Track Name (124 BPM)`).
- **Native CUE Sheet Export**: Produces standardized `.cue` sheets formatted with CD-Audio frame indices (`MM:SS:FF`) for DJ software and media players.

### 4. Modern Multi-Tab Streamlit Studio UI (`app.py`)
- **Tab 1 — Tracklist & Inspector**: Upload tracks, view a DataFrame of per-track engineering metrics (Duration, dBFS, detected BPM, RMS Energy), select sort strategies (Smart BPM Sort, Manual Order, Shuffle), and preview individual waveforms.
- **Tab 2 — Mix & Master Console**: Configure normalization targets, silence stripping thresholds, crossfade durations, and filter curves; generate the master mix, view the master waveform and fade comparisons, and download `.mp3`.
- **Tab 3 — Video & YouTube Publisher**: Live preview styled cover art, toggle the dynamic waveform visualizer, render and download `.mp4` video, and copy/download YouTube descriptions and `.cue` sheets. All state is maintained in `st.session_state`.

---

## Project Structure

```text
mixtape-generator/
├── app.py                      # Multi-tab Streamlit Studio UI
├── main.py                     # Feature-complete CLI engine
├── requirements.txt            # Python dependencies (pydub, pillow, librosa, streamlit, etc.)
├── packages.txt                # System packages (ffmpeg) for cloud hosting
├── src/
│   ├── __init__.py
│   ├── audio_inspector.py      # Loudness normalization, silence trimming, BPM analysis & plotting
│   ├── mixer.py                # DSP crossfade curves (constant-power, EQ swap, bass swap) & smart sort
│   ├── description_generator.py# YouTube tracklist timestamps & CUE sheet generator
│   └── video_generator.py      # Cover art studio & dynamic FFmpeg showwaves MP4 renderer
└── tests/
    └── test_pipeline.py        # Comprehensive unit tests
```

---

## Prerequisites

- Python 3.9+ (tested up to Python 3.14)
- **FFmpeg** installed and available on your system `PATH` (required by `pydub` and `video_generator.py`).

---

## Local Setup

```bash
# 1. Activate your virtual environment
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Usage

### 1. Launch the Streamlit Studio Web UI
```bash
streamlit run app.py
```

### 2. Command-Line Interface (CLI)
```bash
python main.py \
  --tracks input_tracks \
  --image assets/cover.jpg \
  --name "Deep Afro Summer Mix" \
  --genre "Afro House" \
  --smart-sort \
  --normalize \
  --trim-silence \
  --curve club_bass_swap \
  --transition-ms 6000 \
  --blur-background \
  --overlay-title \
  --visualizer \
  --waveform
```

### 3. Run Automated Tests
```bash
python -m unittest discover -s tests -v
```
