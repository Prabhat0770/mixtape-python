"""YouTube description and CUE sheet timestamp generator."""

import os
from typing import Any, Dict, List, Optional

from pydub import AudioSegment

SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a")


def _format_timestamp(seconds: int) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_cue_index(ms: int) -> str:
    """Format milliseconds into CUE sheet mm:ss:ff (75 frames/second)."""
    total_seconds = ms // 1000
    rem_ms = ms % 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    frames = min(74, int(round((rem_ms * 75.0) / 1000.0)))
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def _load_tracks_info(
    track_folder: Optional[str] = None,
    track_metadata: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Resolve track info from either track_metadata or directory listing."""
    if track_metadata is not None:
        return track_metadata
    elif track_folder is not None:
        if not os.path.isdir(track_folder):
            raise FileNotFoundError(f"Track folder not found: {track_folder}")
        files = sorted(
            f
            for f in os.listdir(track_folder)
            if f.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)
        )
        tracks_info: List[Dict[str, Any]] = []
        for f in files:
            audio = AudioSegment.from_file(os.path.join(track_folder, f))
            tracks_info.append(
                {
                    "filename": f,
                    "title": os.path.splitext(f)[0],
                    "duration_ms": len(audio),
                }
            )
        return tracks_info
    else:
        raise ValueError("Either track_folder or track_metadata must be provided.")


def generate_youtube_description_with_timestamps(
    track_folder: Optional[str] = None,
    mixtape_name: str = "Afro House Mixtape",
    genre: str = "Afro House",
    start_time_sec: int = 0,
    track_metadata: Optional[List[Dict[str, Any]]] = None,
    overlap_ms: int = 0,
    save_path: Optional[str] = None,
) -> str:
    """
    Generate a YouTube description with tracklist, timestamps (with BPM if detected), and hashtags.

    If `track_metadata` is provided (from `smooth_fade_mixtape`), timestamps reflect
    the exact playback order and crossfade overlap. Otherwise, reads and sorts files
    alphabetically from `track_folder`.
    """
    tracks_info = _load_tracks_info(track_folder, track_metadata)

    if not tracks_info:
        return "No audio tracks found in the folder!"

    lines = [
        f"🔥 {mixtape_name} 🔥",
        f"Genre: {genre}",
        "",
        "🎵 Tracklist:",
    ]

    current_ms = start_time_sec * 1000
    for idx, track in enumerate(tracks_info):
        timestamp = _format_timestamp(max(0, current_ms // 1000))
        bpm = track.get("bpm")
        bpm_suffix = f" ({int(round(bpm))} BPM)" if bpm and bpm > 0 else ""
        lines.append(f"{timestamp} - {track['title']}{bpm_suffix}")

        duration_ms = track["duration_ms"]
        effective_overlap = min(overlap_ms, duration_ms) if idx < len(tracks_info) - 1 else 0
        current_ms += max(0, duration_ms - effective_overlap)

    genre_tag = "#" + "".join(word.capitalize() for word in genre.split())
    hashtags = [
        genre_tag,
        "#HouseMusic",
        "#EDM",
        "#DanceMusic",
        "#Mixtape",
        "#ElectronicMusic",
        "#DJMix",
        "#PartyMusic",
        "#DeepHouse",
        "#MixtapeVibes",
    ]
    # Deduplicate while preserving order
    unique_hashtags = list(dict.fromkeys(hashtags))

    lines.extend(
        [
            "",
            "💽 Download/Listen links:",
            "You can find these tracks online or on Spotify/Apple Music.",
            "",
            f"🎧 Follow for more {genre} mixes!",
            "",
            " ".join(unique_hashtags),
        ]
    )

    description = "\n".join(lines)

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(description)

    return description


def generate_cue_sheet(
    track_metadata: Optional[List[Dict[str, Any]]] = None,
    track_folder: Optional[str] = None,
    audio_filename: str = "mixtape.mp3",
    mixtape_title: str = "Studio DJ Mixtape",
    performer: str = "Various Artists",
    overlap_ms: int = 0,
    save_path: Optional[str] = None,
) -> str:
    """
    Generate an exportable .cue sheet so DJs and media players can read track chapters natively.
    """
    tracks_info = _load_tracks_info(track_folder, track_metadata)

    clean_audio_file = os.path.basename(audio_filename)
    cue_lines = [
        f'PERFORMER "{performer}"',
        f'TITLE "{mixtape_title}"',
        f'FILE "{clean_audio_file}" MP3',
    ]

    current_ms = 0
    for idx, track in enumerate(tracks_info, start=1):
        index_str = _format_cue_index(max(0, current_ms))
        title = track.get("title", f"Track {idx}").replace('"', "'")
        cue_lines.append(f"  TRACK {idx:02d} AUDIO")
        cue_lines.append(f'    TITLE "{title}"')
        cue_lines.append(f'    PERFORMER "{performer}"')
        cue_lines.append(f"    INDEX 01 {index_str}")

        duration_ms = track["duration_ms"]
        effective_overlap = min(overlap_ms, duration_ms) if idx < len(tracks_info) else 0
        current_ms += max(0, duration_ms - effective_overlap)

    cue_content = "\n".join(cue_lines) + "\n"

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(cue_content)

    return cue_content
