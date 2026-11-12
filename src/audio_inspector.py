"""Audio inspection, slicing, fading, normalization, and waveform visualization utilities."""

import os
from typing import Any, Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_leading_silence


def estimate_bpm_and_energy(file_path: str) -> Tuple[float, float]:
    """
    Estimate the BPM (tempo) and RMS energy of an audio file.

    Uses librosa if available; falls back cleanly to pydub/numpy metrics on error or missing dependency.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Primary: librosa beat tracking and RMS feature extraction
    try:
        import librosa

        # Load first 60 seconds (or full track if shorter) for snappy analysis
        y, sr = librosa.load(file_path, sr=22050, mono=True, duration=60.0)
        if len(y) > 0 and np.max(np.abs(y)) > 1e-4:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm_val = float(np.atleast_1d(tempo)[0])
            rms_arr = librosa.feature.rms(y=y)
            rms_val = float(np.mean(rms_arr)) if len(rms_arr) > 0 else 0.0
            return round(bpm_val, 1), round(rms_val, 4)
    except Exception:
        pass

    # Fallback: pydub RMS and neutral tempo default
    try:
        audio = AudioSegment.from_file(file_path)
        rms_val = float(audio.rms)
        # Standard mid-tempo house/electronic default if tempo extraction unavailable
        return 120.0, round(rms_val, 2)
    except Exception:
        return 120.0, 0.0


def trim_silence(
    audio: AudioSegment,
    silence_threshold: float = -50.0,
    chunk_size: int = 10,
) -> AudioSegment:
    """
    Strip leading and trailing silence from an AudioSegment using pydub.silence.detect_leading_silence.

    Ensures seamless transitions without dead air.
    """
    if len(audio) == 0:
        return audio

    start_trim = detect_leading_silence(
        audio, silence_threshold=silence_threshold, chunk_size=chunk_size
    )
    end_trim = detect_leading_silence(
        audio.reverse(), silence_threshold=silence_threshold, chunk_size=chunk_size
    )

    duration = len(audio)
    if start_trim + end_trim >= duration:
        # If the whole track is below silence threshold, preserve original
        return audio

    return audio[start_trim : duration - end_trim]


def normalize_loudness(
    audio: AudioSegment,
    target_dBFS: float = -14.0,
    headroom_dB: float = 0.5,
) -> AudioSegment:
    """
    Normalize audio to a target loudness (default -14.0 dBFS, YouTube standard)
    with peak headroom protection against clipping.
    """
    if audio.dBFS == -float("inf") or len(audio) == 0:
        return audio

    gain_needed = target_dBFS - audio.dBFS

    # Peak headroom protection: ensure max peak does not exceed -headroom_dB (e.g., -0.5 dBFS)
    current_max = audio.max_dBFS
    if current_max + gain_needed > -headroom_dB:
        gain_needed = -headroom_dB - current_max

    return audio.apply_gain(gain_needed)


def inspect_audio(file_path: str) -> Dict[str, Any]:
    """Load an audio file and return audio engineering properties including BPM and energy."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    audio = AudioSegment.from_file(file_path)
    bpm, energy = estimate_bpm_and_energy(file_path)

    return {
        "duration_ms": len(audio),
        "channels": audio.channels,
        "frame_rate": audio.frame_rate,
        "sample_width": audio.sample_width,
        "dBFS": round(audio.dBFS, 2),
        "bpm": bpm,
        "rms_energy": energy,
    }


def slice_audio(audio: AudioSegment, start_ms: int, end_ms: int) -> AudioSegment:
    """Return a slice of an AudioSegment between start_ms and end_ms."""
    return audio[start_ms:end_ms]


def apply_fades(
    audio_clip: AudioSegment,
    fade_in_ms: int = 3000,
    fade_out_ms: int = 3000,
) -> Tuple[AudioSegment, AudioSegment]:
    """Return separate fade-in and fade-out versions of an audio clip."""
    fade_in_clip = audio_clip.fade_in(min(fade_in_ms, len(audio_clip)))
    fade_out_clip = audio_clip.fade_out(min(fade_out_ms, len(audio_clip)))
    return fade_in_clip, fade_out_clip


def concatenate_clips(*clips: AudioSegment) -> AudioSegment:
    """Concatenate two or more AudioSegment clips sequentially."""
    if not clips:
        raise ValueError("At least one AudioSegment clip is required.")

    combined = clips[0]
    for clip in clips[1:]:
        combined += clip
    return combined


def plot_waveform(
    file_path: str,
    output_image: Optional[str] = None,
    title: str = "Waveform of Audio",
) -> plt.Figure:
    """Plot the audio waveform using librosa if available, or pydub samples as fallback."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    fig, ax = plt.subplots(figsize=(12, 3))

    try:
        import librosa
        import librosa.display

        y, sr = librosa.load(file_path, sr=None)
        librosa.display.waveshow(y, sr=sr, ax=ax, color="#1f77b4")
    except Exception:
        audio = AudioSegment.from_file(file_path).set_channels(1)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if len(samples) > 0:
            max_val = np.max(np.abs(samples)) or 1.0
            samples = samples / max_val
        time_axis = np.linspace(0, len(audio) / 1000.0, num=len(samples))
        step = max(1, len(samples) // 5000)
        ax.plot(time_axis[::step], samples[::step], color="#1f77b4", linewidth=0.7)
        ax.set_xlabel("Time (s)")

    ax.set_title(title)
    ax.set_ylabel("Amplitude")
    fig.tight_layout()

    if output_image:
        os.makedirs(os.path.dirname(output_image) or ".", exist_ok=True)
        fig.savefig(output_image, dpi=150)

    return fig


def plot_fade_comparison(
    fade_in_clip: AudioSegment,
    fade_out_clip: AudioSegment,
    output_image: Optional[str] = None,
) -> plt.Figure:
    """Plot fade-in and fade-out waveforms side by side."""
    fade_in_samples = fade_in_clip.get_array_of_samples()
    fade_out_samples = fade_out_clip.get_array_of_samples()

    fig, axes = plt.subplots(2, 1, figsize=(12, 5), sharex=True)
    axes[0].plot(fade_in_samples, color="#2ca02c", linewidth=0.6)
    axes[0].set_title("Fade-In Waveform")
    axes[1].plot(fade_out_samples, color="#d62728", linewidth=0.6)
    axes[1].set_title("Fade-Out Waveform")
    fig.tight_layout()

    if output_image:
        os.makedirs(os.path.dirname(output_image) or ".", exist_ok=True)
        fig.savefig(output_image, dpi=150)

    return fig
