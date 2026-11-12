"""CLI entry point for the Studio DJ Mixtape & Video Production Engine."""

import argparse
import os

from src import (
    generate_cue_sheet,
    generate_youtube_description_with_timestamps,
    make_video_from_audio_optimized,
    plot_waveform,
    smooth_fade_mixtape,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a studio-grade mixtape, YouTube description, CUE sheet, and MP4 video."
    )
    parser.add_argument(
        "--tracks",
        default="input_tracks",
        help="Folder containing input audio tracks (default: input_tracks)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Optional cover image path to render an MP4 video",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated outputs (default: output)",
    )
    parser.add_argument(
        "--name",
        default="Afro House Summer Mix",
        help="Mixtape title for the YouTube description and cover badge",
    )
    parser.add_argument(
        "--genre",
        default="Afro House",
        help="Music genre for the YouTube description, hashtags, and cover badge",
    )
    parser.add_argument(
        "--transition-ms",
        type=int,
        default=6000,
        help="Crossfade duration in milliseconds (default: 6000)",
    )
    parser.add_argument(
        "--curve",
        "--transition-curve",
        dest="curve",
        default="constant_power",
        choices=["constant_power", "eq_swap", "club_bass_swap"],
        help="Transition crossfade curve (default: constant_power)",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize every track to target dBFS with peak headroom protection before crossfading",
    )
    parser.add_argument(
        "--target-dbfs",
        type=float,
        default=-14.0,
        help="Target loudness in dBFS for normalization (default: -14.0 for YouTube)",
    )
    parser.add_argument(
        "--trim-silence",
        action="store_true",
        help="Strip leading and trailing silence from each track before mixing",
    )
    parser.add_argument(
        "--smart-sort",
        action="store_true",
        help="Sort tracks smoothly by tempo/energy curve (Smart Harmonic/BPM Sort)",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Keep tracks sorted alphabetically instead of shuffling",
    )
    parser.add_argument(
        "--blur-background",
        action="store_true",
        help="Blur-fill background when cover image aspect ratio differs from 16:9",
    )
    parser.add_argument(
        "--overlay-title",
        action="store_true",
        help="Render sleek semi-transparent title and genre badge on cover art",
    )
    parser.add_argument(
        "--visualizer",
        action="store_true",
        help="Render dynamic audio waveform overlay on video using FFmpeg showwaves filter",
    )
    parser.add_argument(
        "--cue",
        action="store_true",
        default=True,
        help="Generate an exportable .cue sheet alongside YouTube description (default: True)",
    )
    parser.add_argument(
        "--waveform",
        action="store_true",
        help="Save a PNG waveform image of the generated mixtape",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    mixtape_audio_path = os.path.join(args.output_dir, "mixtape.mp3")
    description_path = os.path.join(args.output_dir, "youtube_description.txt")
    cue_path = os.path.join(args.output_dir, "mixtape.cue")
    video_path = os.path.join(args.output_dir, "mixtape_video.mp4")

    # Determine sort mode
    if args.smart_sort:
        sort_mode = "smart"
    elif args.no_shuffle:
        sort_mode = "manual"
    else:
        sort_mode = "shuffle"

    print("Building studio mixtape...")
    audio_out, track_metadata = smooth_fade_mixtape(
        folder=args.tracks,
        output=mixtape_audio_path,
        transition_ms=args.transition_ms,
        sort_mode=sort_mode,
        transition_curve=args.curve,
        trim_silence_enabled=args.trim_silence,
        normalize_enabled=args.normalize,
        target_dBFS=args.target_dbfs,
    )
    print(f"Mixtape audio saved to: {audio_out}")

    description = generate_youtube_description_with_timestamps(
        mixtape_name=args.name,
        genre=args.genre,
        track_metadata=track_metadata,
        overlap_ms=args.transition_ms,
        save_path=description_path,
    )
    print(f"YouTube description saved to: {description_path}")
    print("\n" + description + "\n")

    if args.cue:
        cue_sheet = generate_cue_sheet(
            track_metadata=track_metadata,
            audio_filename=os.path.basename(audio_out),
            mixtape_title=args.name,
            performer=args.genre,
            overlap_ms=args.transition_ms,
            save_path=cue_path,
        )
        print(f"CUE sheet saved to: {cue_path}")

    if args.waveform:
        waveform_path = os.path.join(args.output_dir, "mixtape_waveform.png")
        plot_waveform(audio_out, output_image=waveform_path, title=f"{args.name} Waveform")
        print(f"Waveform image saved to: {waveform_path}")

    if args.image:
        print("Rendering MP4 video with FFmpeg...")
        video_out = make_video_from_audio_optimized(
            image_path=args.image,
            audio_path=audio_out,
            output_path=video_path,
            blur_background=args.blur_background,
            overlay_badge=args.overlay_title,
            title=args.name,
            genre=args.genre,
            visualizer=args.visualizer,
        )
        print(f"Mixtape video saved to: {video_out}")


if __name__ == "__main__":
    main()
