"""Comprehensive unit tests for the Studio DJ Mixtape & Video Production Engine."""

import os
import tempfile
import unittest

from PIL import Image
from pydub import AudioSegment
from pydub.generators import Sine

from src import (
    apply_club_bass_swap_crossfade,
    apply_constant_power_crossfade,
    apply_eq_swap_crossfade,
    apply_fades,
    concatenate_clips,
    estimate_bpm_and_energy,
    generate_cue_sheet,
    generate_youtube_description_with_timestamps,
    inspect_audio,
    make_video_from_audio_optimized,
    normalize_loudness,
    plot_fade_comparison,
    plot_waveform,
    process_cover_image,
    slice_audio,
    smart_bpm_sort,
    smooth_fade_mixtape,
    trim_silence,
)


class TestMixtapePipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tracks_dir = os.path.join(self.tmp_dir.name, "tracks")
        self.out_dir = os.path.join(self.tmp_dir.name, "output")
        os.makedirs(self.tracks_dir, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)

        # Create two 4-second synthetic MP3 tracks
        track1 = Sine(440).to_audio_segment(duration=4000)
        track2 = Sine(554).to_audio_segment(duration=4000)
        self.track1_path = os.path.join(self.tracks_dir, "01_track_one.mp3")
        self.track2_path = os.path.join(self.tracks_dir, "02_track_two.mp3")

        with open(self.track1_path, "wb") as f:
            track1.export(f, format="mp3")
        with open(self.track2_path, "wb") as f:
            track2.export(f, format="mp3")

        # Create a synthetic cover image (square aspect ratio to test blur-fit)
        self.cover_path = os.path.join(self.tmp_dir.name, "cover.png")
        Image.new("RGBA", (600, 600), color=(30, 144, 255, 255)).save(self.cover_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_audio_inspector_basics(self):
        info = inspect_audio(self.track1_path)
        self.assertGreaterEqual(info["duration_ms"], 3900)
        self.assertIn("dBFS", info)
        self.assertIn("bpm", info)
        self.assertIn("rms_energy", info)

        audio = AudioSegment.from_file(self.track1_path)
        sliced = slice_audio(audio, 0, 2000)
        self.assertEqual(len(sliced), 2000)

        fade_in, fade_out = apply_fades(sliced, fade_in_ms=1000, fade_out_ms=1000)
        self.assertEqual(len(fade_in), 2000)
        self.assertEqual(len(fade_out), 2000)

        joined = concatenate_clips(fade_in, fade_out)
        self.assertEqual(len(joined), 4000)

        # Fade comparison plot
        fade_plot = plot_fade_comparison(fade_in, fade_out)
        self.assertIsNotNone(fade_plot)

    def test_silence_trimming(self):
        tone = Sine(440).to_audio_segment(duration=2000)
        silence = AudioSegment.silent(duration=1000)
        padded = silence + tone + silence
        self.assertEqual(len(padded), 4000)

        trimmed = trim_silence(padded, silence_threshold=-40.0)
        # Should strip approximately 2000ms of silence
        self.assertLess(len(trimmed), 3000)
        self.assertGreaterEqual(len(trimmed), 1950)

    def test_loudness_normalization(self):
        tone = Sine(440).to_audio_segment(duration=1000).apply_gain(-25.0)
        target = -14.0
        normalized = normalize_loudness(tone, target_dBFS=target, headroom_dB=0.5)

        self.assertAlmostEqual(normalized.dBFS, target, delta=1.5)
        self.assertLessEqual(normalized.max_dBFS, -0.4)

    def test_estimate_bpm_and_energy(self):
        bpm, energy = estimate_bpm_and_energy(self.track1_path)
        self.assertIsInstance(bpm, float)
        self.assertIsInstance(energy, float)
        self.assertGreaterEqual(bpm, 0.0)

    def test_transition_curves(self):
        s1 = Sine(300).to_audio_segment(duration=3000).set_channels(2).set_frame_rate(44100)
        s2 = Sine(600).to_audio_segment(duration=3000).set_channels(2).set_frame_rate(44100)

        # 1. Constant-power crossfade
        cp = apply_constant_power_crossfade(s1, s2)
        self.assertEqual(len(cp), 3000)

        # 2. EQ filter swap
        eq = apply_eq_swap_crossfade(s1, s2)
        self.assertEqual(len(eq), 3000)

        # 3. Club bass-swap
        bass = apply_club_bass_swap_crossfade(s1, s2)
        self.assertEqual(len(bass), 3000)

    def test_smart_bpm_sort(self):
        tracks = [
            {"filename": "c.mp3", "bpm": 128.0, "rms_energy": 0.5},
            {"filename": "a.mp3", "bpm": 120.0, "rms_energy": 0.3},
            {"filename": "b.mp3", "bpm": 124.0, "rms_energy": 0.4},
        ]
        sorted_tracks = smart_bpm_sort(tracks)
        self.assertEqual([t["filename"] for t in sorted_tracks], ["a.mp3", "b.mp3", "c.mp3"])

    def test_cover_image_studio_and_badge(self):
        styled_path = os.path.join(self.out_dir, "styled_cover.jpg")
        process_cover_image(
            image_path=self.cover_path,
            output_path=styled_path,
            target_resolution=(1280, 720),
            blur_background=True,
            overlay_badge=True,
            title="Studio Afro Mix",
            genre="Afro House",
        )
        self.assertTrue(os.path.exists(styled_path))
        with Image.open(styled_path) as img:
            self.assertEqual(img.size, (1280, 720))

    def test_cue_sheet_generation(self):
        metadata = [
            {"title": "Track One", "duration_ms": 180000},
            {"title": "Track Two", "duration_ms": 200000},
        ]
        cue_path = os.path.join(self.out_dir, "mixtape.cue")
        cue_text = generate_cue_sheet(
            track_metadata=metadata,
            audio_filename="mixtape.mp3",
            mixtape_title="Test Mix",
            performer="DJ Test",
            overlap_ms=6000,
            save_path=cue_path,
        )
        self.assertTrue(os.path.exists(cue_path))
        self.assertIn('TITLE "Test Mix"', cue_text)
        self.assertIn('FILE "mixtape.mp3" MP3', cue_text)
        self.assertIn("TRACK 01 AUDIO", cue_text)
        self.assertIn("INDEX 01 00:00:00", cue_text)
        self.assertIn("TRACK 02 AUDIO", cue_text)

    def test_youtube_description_with_bpm(self):
        metadata = [
            {"title": "Track One", "duration_ms": 60000, "bpm": 124.0},
            {"title": "Track Two", "duration_ms": 60000, "bpm": 126.0},
        ]
        desc = generate_youtube_description_with_timestamps(
            mixtape_name="Summer Afro",
            genre="Afro House",
            track_metadata=metadata,
            overlap_ms=5000,
        )
        self.assertIn("00:00 - Track One (124 BPM)", desc)
        self.assertIn("00:55 - Track Two (126 BPM)", desc)
        self.assertIn("#AfroHouse", desc)

    def test_video_with_dynamic_visualizer(self):
        video_path = os.path.join(self.out_dir, "visualizer_test.mp4")
        video_out = make_video_from_audio_optimized(
            image_path=self.cover_path,
            audio_path=self.track1_path,
            output_path=video_path,
            video_resolution=(640, 360),
            fps=24,
            preset="ultrafast",
            blur_background=True,
            overlay_badge=True,
            title="Visualizer Test",
            genre="House",
            visualizer=True,
        )
        self.assertTrue(os.path.exists(video_out))
        self.assertGreater(os.path.getsize(video_out), 1000)

    def test_full_mixtape_pipeline_all_modes(self):
        mixtape_path = os.path.join(self.out_dir, "mixtape.mp3")
        audio_out, metadata = smooth_fade_mixtape(
            folder=self.tracks_dir,
            output=mixtape_path,
            transition_ms=1500,
            sort_mode="smart",
            transition_curve="club_bass_swap",
            trim_silence_enabled=True,
            normalize_enabled=True,
            target_dBFS=-14.0,
        )
        self.assertTrue(os.path.exists(audio_out))
        self.assertEqual(len(metadata), 2)
        self.assertIn("bpm", metadata[0])

        desc_path = os.path.join(self.out_dir, "description.txt")
        desc = generate_youtube_description_with_timestamps(
            mixtape_name="Test Mix",
            genre="Afro House",
            track_metadata=metadata,
            overlap_ms=1500,
            save_path=desc_path,
        )
        self.assertTrue(os.path.exists(desc_path))
        self.assertIn("01_track_one", desc)

        wave_path = os.path.join(self.out_dir, "waveform.png")
        plot_waveform(audio_out, output_image=wave_path)
        self.assertTrue(os.path.exists(wave_path))


if __name__ == "__main__":
    unittest.main()
