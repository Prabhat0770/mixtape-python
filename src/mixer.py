"""Mixtape audio blending and studio DSP crossfade engine."""

import os
import random
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydub import AudioSegment

from .audio_inspector import (
    estimate_bpm_and_energy,
    normalize_loudness,
    trim_silence,
)

SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a")

TRANSITION_EQ_SWAP = "EQ Filter Swap (Low-Pass/High-Pass)"
TRANSITION_CONSTANT_POWER = "Constant-Power Crossfade"
TRANSITION_CLUB_BASS_SWAP = "Club Bass-Swap"


def apply_constant_power_crossfade(
    outgoing_segment: AudioSegment,
    incoming_segment: AudioSegment,
) -> AudioSegment:
    """
    Apply mathematically exact equal-power (constant-power) crossfade.

    Uses cosine/sine gains (gain_out^2 + gain_in^2 = 1) across the overlap
    to eliminate the mid-transition 3dB volume drop of linear fades.
    """
    overlap_ms = min(len(outgoing_segment), len(incoming_segment))
    if overlap_ms <= 0:
        return outgoing_segment + incoming_segment

    seg1 = outgoing_segment[-overlap_ms:]
    seg2 = incoming_segment[:overlap_ms]

    arr1 = np.array(seg1.get_array_of_samples(), dtype=np.float32)
    arr2 = np.array(seg2.get_array_of_samples(), dtype=np.float32)

    channels = seg1.channels
    num_frames = min(len(arr1), len(arr2)) // channels
    if num_frames <= 0:
        return seg1.overlay(seg2)

    # Truncate arrays to identical frame count
    total_samples = num_frames * channels
    arr1 = arr1[:total_samples]
    arr2 = arr2[:total_samples]

    # Compute constant-power curve
    t = np.linspace(0.0, 1.0, num_frames, dtype=np.float32)
    gain_out = np.cos(t * (np.pi / 2.0))
    gain_in = np.sin(t * (np.pi / 2.0))

    if channels > 1:
        gain_out = np.repeat(gain_out, channels)
        gain_in = np.repeat(gain_in, channels)

    blended = np.clip(arr1 * gain_out + arr2 * gain_in, -32768, 32767).astype(np.int16)

    return AudioSegment(
        blended.tobytes(),
        frame_rate=seg1.frame_rate,
        sample_width=seg1.sample_width,
        channels=channels,
    )


def apply_eq_swap_crossfade(
    outgoing_segment: AudioSegment,
    incoming_segment: AudioSegment,
) -> AudioSegment:
    """
    DJ EQ Filter Swap transition:
    Outgoing track gets rolled off with a low-pass filter (2500Hz) while fading out,
    while incoming track opens up with a high-pass filter (250Hz) while fading in.
    """
    overlap_ms = min(len(outgoing_segment), len(incoming_segment))
    seg1 = outgoing_segment[-overlap_ms:]
    seg2 = incoming_segment[:overlap_ms]

    out_filt = seg1.fade_out(overlap_ms).low_pass_filter(2500)
    in_filt = seg2.fade_in(overlap_ms).high_pass_filter(250)

    return out_filt.overlay(in_filt)


def apply_club_bass_swap_crossfade(
    outgoing_segment: AudioSegment,
    incoming_segment: AudioSegment,
) -> AudioSegment:
    """
    Club Bass-Swap transition:
    Splits both tracks at 250Hz into low-end (sub/kick) and mid/highs.
    Mid/highs crossfade with constant-power across the entire duration.
    Bass is swapped right at the midpoint (T/2) with rapid 100ms mini-fades
    to give that punchy club transition where the new bassline drops cleanly.
    """
    overlap_ms = min(len(outgoing_segment), len(incoming_segment))
    seg1 = outgoing_segment[-overlap_ms:]
    seg2 = incoming_segment[:overlap_ms]

    # Split into low band and mid-high band
    seg1_bass = seg1.low_pass_filter(250)
    seg1_mids = seg1.high_pass_filter(250)
    seg2_bass = seg2.low_pass_filter(250)
    seg2_mids = seg2.high_pass_filter(250)

    # Constant power crossfade for mid/high frequencies
    mids_crossfade = apply_constant_power_crossfade(seg1_mids, seg2_mids)

    # Bass swap at midpoint
    mid_point = overlap_ms // 2
    quick_fade = min(100, max(10, mid_point // 2))

    b1 = seg1_bass[:mid_point].fade_out(quick_fade)
    b2 = seg2_bass[mid_point:].fade_in(quick_fade)
    bass_swap = b1 + b2

    # Align lengths if rounding difference
    if len(bass_swap) != len(mids_crossfade):
        target_len = min(len(bass_swap), len(mids_crossfade))
        bass_swap = bass_swap[:target_len]
        mids_crossfade = mids_crossfade[:target_len]

    return mids_crossfade.overlay(bass_swap)


def render_transition(
    outgoing_segment: AudioSegment,
    incoming_segment: AudioSegment,
    curve: str = "constant_power",
) -> AudioSegment:
    """Render transition between outgoing and incoming audio clips using selected curve."""
    curve_norm = curve.lower().replace("-", "_").replace(" ", "_")
    if "eq" in curve_norm or "filter" in curve_norm:
        return apply_eq_swap_crossfade(outgoing_segment, incoming_segment)
    elif "bass" in curve_norm or "club" in curve_norm:
        return apply_club_bass_swap_crossfade(outgoing_segment, incoming_segment)
    else:
        # Default: Constant-Power Crossfade
        return apply_constant_power_crossfade(outgoing_segment, incoming_segment)


def smart_bpm_sort(tracks_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Smart Harmonic/BPM Sort:
    Orders tracks smoothly by tempo (BPM) ascending to build energy over the mix,
    using RMS energy as a secondary tie-breaker.
    """
    return sorted(
        tracks_info,
        key=lambda item: (item.get("bpm", 120.0), item.get("rms_energy", 0.0)),
    )


def smooth_fade_mixtape(
    folder: str,
    output: str = "output/mixtape.mp3",
    transition_ms: int = 6000,
    shuffle: Optional[bool] = None,
    sort_mode: str = "smart",
    transition_curve: str = "constant_power",
    trim_silence_enabled: bool = True,
    normalize_enabled: bool = True,
    target_dBFS: float = -14.0,
    ordered_files: Optional[List[str]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Combine all audio tracks in a folder into a studio-grade mixtape with smooth crossfades.

    Args:
        folder: Path to directory containing audio files.
        output: Destination MP3 file path.
        transition_ms: Duration of crossfade overlap in milliseconds.
        shuffle: Legacy boolean flag. If provided, overrides sort_mode (True -> shuffle, False -> manual).
        sort_mode: 'smart' (Smart Harmonic/BPM Sort), 'shuffle', or 'manual'.
        transition_curve: 'constant_power', 'eq_swap', or 'club_bass_swap'.
        trim_silence_enabled: Whether to strip leading/trailing silence from each track.
        normalize_enabled: Whether to normalize tracks to target_dBFS with peak headroom protection.
        target_dBFS: YouTube standard loudness target (-14.0 dBFS by default).
        ordered_files: Optional explicit list of filenames to mix in exact order.

    Returns:
        Tuple of (output_file_path, list of track metadata dicts).
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Track folder not found: {folder}")

    if ordered_files:
        files = [f for f in ordered_files if f.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)]
    else:
        files = sorted(
            f for f in os.listdir(folder) if f.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)
        )

    if not files:
        raise ValueError(f"No supported audio files found in: {folder}")

    # Resolve sort mode from legacy shuffle parameter if provided
    effective_sort = sort_mode.lower()
    if shuffle is not None:
        effective_sort = "shuffle" if shuffle else "manual"

    # Analyze metadata for each track
    analyzed_tracks: List[Dict[str, Any]] = []
    for file_name in files:
        file_path = os.path.join(folder, file_name)
        bpm, energy = estimate_bpm_and_energy(file_path)
        analyzed_tracks.append(
            {
                "filename": file_name,
                "file_path": file_path,
                "title": os.path.splitext(file_name)[0],
                "bpm": bpm,
                "rms_energy": energy,
            }
        )

    # Apply sorting strategy
    if effective_sort == "smart":
        tracks_to_mix = smart_bpm_sort(analyzed_tracks)
    elif effective_sort == "shuffle":
        tracks_to_mix = list(analyzed_tracks)
        random.shuffle(tracks_to_mix)
    else:
        tracks_to_mix = analyzed_tracks

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    mixtape: Optional[AudioSegment] = None
    track_metadata: List[Dict[str, Any]] = []

    for item in tracks_to_mix:
        file_path = item["file_path"]
        song = AudioSegment.from_file(file_path)
        song = song.set_channels(2).set_frame_rate(44100)

        # 1. Strip leading and trailing silence
        if trim_silence_enabled:
            song = trim_silence(song)

        # 2. Normalize loudness to target dBFS with peak headroom protection
        if normalize_enabled:
            song = normalize_loudness(song, target_dBFS=target_dBFS)

        item_meta = {
            "filename": item["filename"],
            "title": item["title"],
            "duration_ms": len(song),
            "dBFS": round(song.dBFS, 2),
            "bpm": item["bpm"],
            "energy": item["rms_energy"],
        }
        track_metadata.append(item_meta)

        if mixtape is None:
            mixtape = song
        else:
            overlap = min(transition_ms, len(song), len(mixtape))
            if overlap > 0:
                outgoing = mixtape[-overlap:]
                incoming = song[:overlap]
                transition = render_transition(outgoing, incoming, curve=transition_curve)
                mixtape = mixtape[:-overlap] + transition + song[overlap:]
            else:
                mixtape = mixtape + song

    if mixtape is None:
        raise ValueError("No audio content could be generated.")

    with open(output, "wb") as f_out:
        mixtape.export(f_out, format="mp3")
    return output, track_metadata
