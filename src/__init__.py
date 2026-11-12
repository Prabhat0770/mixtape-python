"""Studio DJ Mixtape & YouTube Video Production Engine core package."""

from .audio_inspector import (
    apply_fades,
    concatenate_clips,
    estimate_bpm_and_energy,
    inspect_audio,
    normalize_loudness,
    plot_fade_comparison,
    plot_waveform,
    slice_audio,
    trim_silence,
)
from .description_generator import (
    generate_cue_sheet,
    generate_youtube_description_with_timestamps,
)
from .mixer import (
    TRANSITION_CLUB_BASS_SWAP,
    TRANSITION_CONSTANT_POWER,
    TRANSITION_EQ_SWAP,
    apply_club_bass_swap_crossfade,
    apply_constant_power_crossfade,
    apply_eq_swap_crossfade,
    smart_bpm_sort,
    smooth_fade_mixtape,
)
from .video_generator import (
    make_video_from_audio_optimized,
    process_cover_image,
)

__all__ = [
    "inspect_audio",
    "estimate_bpm_and_energy",
    "trim_silence",
    "normalize_loudness",
    "slice_audio",
    "apply_fades",
    "concatenate_clips",
    "plot_waveform",
    "plot_fade_comparison",
    "smooth_fade_mixtape",
    "smart_bpm_sort",
    "apply_constant_power_crossfade",
    "apply_eq_swap_crossfade",
    "apply_club_bass_swap_crossfade",
    "TRANSITION_EQ_SWAP",
    "TRANSITION_CONSTANT_POWER",
    "TRANSITION_CLUB_BASS_SWAP",
    "generate_youtube_description_with_timestamps",
    "generate_cue_sheet",
    "process_cover_image",
    "make_video_from_audio_optimized",
]
