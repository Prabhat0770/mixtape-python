"""Studio-grade DJ Mixtape & YouTube Video Production Engine Web UI."""

import io
import os
import tempfile
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from pydub import AudioSegment
import streamlit as st

from src import (
    TRANSITION_CLUB_BASS_SWAP,
    TRANSITION_CONSTANT_POWER,
    TRANSITION_EQ_SWAP,
    apply_fades,
    generate_cue_sheet,
    generate_youtube_description_with_timestamps,
    inspect_audio,
    make_video_from_audio_optimized,
    plot_fade_comparison,
    plot_waveform,
    process_cover_image,
    smooth_fade_mixtape,
)

# Page configuration
st.set_page_config(
    page_title="Studio DJ Mixtape & Video Engine",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Studio CSS Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B, #FF8A00, #4A90E2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-caption {
        font-size: 1rem;
        color: #8892b0;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #111927;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .metric-val {
        font-size: 1.6rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "track_files" not in st.session_state:
    st.session_state["track_files"] = []
if "analyzed_tracks" not in st.session_state:
    st.session_state["analyzed_tracks"] = []
if "master_audio_bytes" not in st.session_state:
    st.session_state["master_audio_bytes"] = None
if "master_metadata" not in st.session_state:
    st.session_state["master_metadata"] = None
if "description_text" not in st.session_state:
    st.session_state["description_text"] = ""
if "cue_text" not in st.session_state:
    st.session_state["cue_text"] = ""
if "video_bytes" not in st.session_state:
    st.session_state["video_bytes"] = None
if "work_dir" not in st.session_state:
    st.session_state["work_dir"] = tempfile.mkdtemp(prefix="mixtape_studio_")


def format_ms(ms: int) -> str:
    """Format milliseconds to MM:SS."""
    secs = max(0, ms // 1000)
    return f"{secs // 60:02d}:{secs % 60:02d}"


# Header
st.markdown('<div class="main-header">🎛️ Studio DJ Mixtape & Video Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-caption">Pro-grade DSP Crossfading, Smart Harmonic BPM Sorting, YouTube SEO Chapters & Dynamic FFmpeg Visualizer</div>',
    unsafe_allow_html=True,
)

# Sidebar: Global Mix Metadata
with st.sidebar:
    st.header("💽 Project Identity")
    mixtape_title = st.text_input("Mixtape Title", value="Afro House Summer Mix", key="cfg_title")
    genre = st.text_input("Genre", value="Afro House", key="cfg_genre")
    performer = st.text_input("DJ / Performer", value="DJ Mixtape Engine", key="cfg_performer")

    st.markdown("---")
    st.header("⚙️ Global Audio Standards")
    target_lufs = st.slider(
        "Loudness Target (dBFS)",
        min_value=-24.0,
        max_value=-8.0,
        value=-14.0,
        step=0.5,
        help="YouTube standard target is -14.0 dBFS with peak headroom limiter.",
    )
    transition_sec = st.slider(
        "Crossfade Duration (s)",
        min_value=1,
        max_value=15,
        value=6,
        help="Overlap duration between adjacent tracks.",
    )

# Studio Tabs
tab1, tab2, tab3 = st.tabs([
    "📂 Tab 1 — Tracklist & Inspector",
    "🎚️ Tab 2 — Mix & Master Console",
    "🎬 Tab 3 — Video & YouTube Publisher",
])

# -----------------------------------------------------------------------------
# TAB 1: Tracklist & Inspector
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("🎵 Track Upload & DSP Audio Inspection")
    uploaded_audio = st.file_uploader(
        "Upload Audio Tracks (MP3, WAV, FLAC, AAC, OGG, M4A)",
        type=["mp3", "wav", "flac", "aac", "ogg", "m4a"],
        accept_multiple_files=True,
    )

    if uploaded_audio:
        # Check if newly uploaded files differ from session state
        existing_names = [t["filename"] for t in st.session_state["analyzed_tracks"]]
        new_files = [f for f in uploaded_audio if f.name not in existing_names]

        if new_files:
            with st.spinner("Analyzing audio DSP properties (BPM, Energy, dBFS)..."):
                for track_file in new_files:
                    disk_path = os.path.join(st.session_state["work_dir"], track_file.name)
                    with open(disk_path, "wb") as f_out:
                        f_out.write(track_file.getbuffer())

                    info = inspect_audio(disk_path)
                    st.session_state["analyzed_tracks"].append(
                        {
                            "filename": track_file.name,
                            "file_path": disk_path,
                            "title": os.path.splitext(track_file.name)[0],
                            "duration_ms": info["duration_ms"],
                            "duration_str": format_ms(info["duration_ms"]),
                            "dBFS": info["dBFS"],
                            "bpm": info["bpm"],
                            "rms_energy": info["rms_energy"],
                            "channels": info["channels"],
                            "frame_rate": info["frame_rate"],
                        }
                    )

    tracks = st.session_state["analyzed_tracks"]

    if tracks:
        # Summary KPI Cards
        total_ms = sum(t["duration_ms"] for t in tracks)
        bpms = [t["bpm"] for t in tracks if t.get("bpm", 0) > 0]
        bpm_range_str = f"{min(bpms):.0f} - {max(bpms):.0f}" if bpms else "N/A"
        avg_dbfs = round(sum(t["dBFS"] for t in tracks) / len(tracks), 1)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-val">{len(tracks)}</div><div class="metric-lbl">Total Tracks</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-val">{format_ms(total_ms)}</div><div class="metric-lbl">Total Run Time</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-val">{bpm_range_str}</div><div class="metric-lbl">BPM Range</div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f'<div class="metric-card"><div class="metric-val">{avg_dbfs} dBFS</div><div class="metric-lbl">Avg Loudness</div></div>',
                unsafe_allow_html=True,
            )

        # Track Ordering Strategy
        st.markdown("### 🔀 Track Order Strategy")
        sort_choice = st.radio(
            "Select Track Sequence Strategy:",
            [
                "Smart Harmonic/BPM Sort (Smooth Tempo & Energy Escalation)",
                "Manual Order (Exact Upload / Custom List)",
                "Shuffle (Randomized Party Mix)",
            ],
            index=0,
            horizontal=True,
        )

        if "Smart" in sort_choice:
            current_order = sorted(tracks, key=lambda x: (x["bpm"], x["rms_energy"]))
        elif "Shuffle" in sort_choice:
            current_order = list(tracks)
        else:
            current_order = tracks

        st.session_state["sorted_tracks"] = current_order

        # Dataframe View
        df = pd.DataFrame(
            [
                {
                    "Order": i + 1,
                    "Title": t["title"],
                    "Filename": t["filename"],
                    "Duration": t["duration_str"],
                    "BPM": f"{t['bpm']:.1f}" if t.get("bpm") else "120.0",
                    "Energy (RMS)": t["rms_energy"],
                    "dBFS": f"{t['dBFS']:.1f}",
                    "Format": f"{t['frame_rate']}Hz / {t['channels']}ch",
                }
                for i, t in enumerate(current_order)
            ]
        )
        st.dataframe(df, use_container_width=True)

        # Waveform Inspector
        st.markdown("### 🔍 Individual Waveform Inspector")
        inspect_target = st.selectbox(
            "Select track to visualize waveform:",
            options=[t["filename"] for t in current_order],
        )
        if inspect_target:
            target_track = next(t for t in current_order if t["filename"] == inspect_target)
            fig = plot_waveform(target_track["file_path"], title=f"Waveform: {target_track['title']}")
            st.pyplot(fig)
            plt.close(fig)
    else:
        st.info("👋 Upload 2 or more audio files above to begin inspecting and sequencing your mixtape.")


# -----------------------------------------------------------------------------
# TAB 2: Mix & Master Console
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🎚️ Master Mix & DSP Crossfade Engine")

    col_ctrl, col_dsp = st.columns([1, 1])
    with col_ctrl:
        st.markdown("#### 🔀 Transition Crossfade Curves")
        transition_curve = st.selectbox(
            "Crossfade Curve:",
            [
                TRANSITION_CONSTANT_POWER,
                TRANSITION_EQ_SWAP,
                TRANSITION_CLUB_BASS_SWAP,
            ],
            index=0,
            help=(
                "• Constant-Power: Sine/cosine gain curves preventing the -3dB volume drop.\n"
                "• EQ Filter Swap: Low-pass roll-off on outgoing track with high-pass fade-in on incoming.\n"
                "• Club Bass-Swap: Punchy bassline switch right at midpoint (T/2) with mid-high constant power."
            ),
        )

    with col_dsp:
        st.markdown("#### 🛡️ Mastering & Dynamic Conditioning")
        enable_silence_trim = st.checkbox(
            "Enable Silence Trimming (Strip dead air before/after)",
            value=True,
            help="Uses pydub detect_leading_silence to strip leading/trailing silence before crossfades.",
        )
        enable_normalization = st.checkbox(
            "Enable Target Loudness Normalization",
            value=True,
            help="Normalizes all tracks to target dBFS with peak headroom limiter to prevent clipping.",
        )

    tracks_to_process = st.session_state.get("sorted_tracks", st.session_state["analyzed_tracks"])

    if st.button("⚡ Generate Master Mixtape", type="primary", use_container_width=True):
        if not tracks_to_process:
            st.error("No tracks available to mix. Upload tracks in Tab 1 first.")
        else:
            with st.spinner("Executing DSP Crossfades, Normalization, and Master Rendering..."):
                master_out_path = os.path.join(st.session_state["work_dir"], "master_mixtape.mp3")

                # Resolve curve alias
                if "Constant" in transition_curve:
                    curve_key = "constant_power"
                elif "EQ" in transition_curve:
                    curve_key = "eq_swap"
                else:
                    curve_key = "club_bass_swap"

                ordered_filenames = [t["filename"] for t in tracks_to_process]

                output_path, track_meta = smooth_fade_mixtape(
                    folder=st.session_state["work_dir"],
                    output=master_out_path,
                    transition_ms=transition_sec * 1000,
                    sort_mode="manual",
                    ordered_files=ordered_filenames,
                    transition_curve=curve_key,
                    trim_silence_enabled=enable_silence_trim,
                    normalize_enabled=enable_normalization,
                    target_dBFS=target_lufs,
                )

                with open(output_path, "rb") as f_in:
                    st.session_state["master_audio_bytes"] = f_in.read()

                st.session_state["master_metadata"] = track_meta
                st.session_state["master_out_path"] = output_path

                # Auto-generate description & cue sheet
                st.session_state["description_text"] = generate_youtube_description_with_timestamps(
                    mixtape_name=mixtape_title,
                    genre=genre,
                    track_metadata=track_meta,
                    overlap_ms=transition_sec * 1000,
                )
                st.session_state["cue_text"] = generate_cue_sheet(
                    track_metadata=track_meta,
                    audio_filename="master_mixtape.mp3",
                    mixtape_title=mixtape_title,
                    performer=performer,
                    overlap_ms=transition_sec * 1000,
                )

            st.success("🎉 Master Mixtape successfully produced and conditioned!")

    # Master Playback and Visualizations
    if st.session_state["master_audio_bytes"] is not None:
        st.markdown("---")
        st.markdown("### 🔊 Master Audio Player")
        st.audio(st.session_state["master_audio_bytes"], format="audio/mp3")

        st.download_button(
            "⬇️ Download Master Mixtape (.mp3)",
            data=st.session_state["master_audio_bytes"],
            file_name=f"{mixtape_title.replace(' ', '_').lower()}.mp3",
            mime="audio/mpeg",
            use_container_width=True,
        )

        # Visualizations
        st.markdown("### 📊 Master Visualizations")
        col_w, col_f = st.columns(2)

        with col_w:
            st.markdown("##### 📈 Full Master Waveform")
            fig_master = plot_waveform(
                st.session_state["master_out_path"],
                title=f"{mixtape_title} (Master Waveform)",
            )
            st.pyplot(fig_master)
            plt.close(fig_master)

        with col_f:
            st.markdown("##### 🎚️ Crossfade Profile Comparison")
            # Synthesize 3-second demo clips for visual fade verification
            demo_clip = AudioSegment.silent(duration=3000)
            if os.path.exists(st.session_state["master_out_path"]):
                src_seg = AudioSegment.from_file(st.session_state["master_out_path"])
                demo_clip = src_seg[:3000]
            f_in, f_out = apply_fades(demo_clip, fade_in_ms=1500, fade_out_ms=1500)
            fig_fades = plot_fade_comparison(f_in, f_out)
            st.pyplot(fig_fades)
            plt.close(fig_fades)


# -----------------------------------------------------------------------------
# TAB 3: Video & YouTube Publisher
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("🎬 Cover Art Studio & YouTube Publisher")

    col_v1, col_v2 = st.columns([1, 1])

    with col_v1:
        st.markdown("#### 🎨 Cover Art Studio")
        uploaded_cover = st.file_uploader(
            "Upload Cover Art Image (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            key="cover_uploader",
        )

        res_choice = st.selectbox(
            "Target Video Resolution",
            ["1280x720 (720p HD)", "1920x1080 (1080p Full HD)"],
            index=0,
        )
        target_res = (1920, 1080) if "1080p" in res_choice else (1280, 720)

        blur_bg = st.checkbox(
            "Blurred Background Fill (Fills 16:9 canvas cleanly)",
            value=True,
            help="Scales and blurs the cover in the background to eliminate black letterbox bars.",
        )
        overlay_badge = st.checkbox(
            "Overlay Semi-Transparent Title & Genre Badge",
            value=True,
            help="Renders glassmorphic typography badge showing Title and Genre on the cover.",
        )

        st.markdown("#### ⚡ FFmpeg Dynamic Visualizer")
        enable_visualizer = st.checkbox(
            "Enable Dynamic Waveform Overlay (FFmpeg showwaves filter)",
            value=False,
            help="Composites a live audio waveform spectrum animation over the cover image.",
        )

    # Process and preview cover art
    cover_image_path = os.path.join(st.session_state["work_dir"], "source_cover.png")
    styled_cover_path = os.path.join(st.session_state["work_dir"], "styled_cover.jpg")

    if uploaded_cover is not None:
        with open(cover_image_path, "wb") as f_c:
            f_c.write(uploaded_cover.getbuffer())
    else:
        # Generate default studio cover if none uploaded
        if not os.path.exists(cover_image_path):
            img_default = Image.new("RGBA", (1000, 1000), (20, 24, 39, 255))
            img_default.save(cover_image_path)

    process_cover_image(
        image_path=cover_image_path,
        output_path=styled_cover_path,
        target_resolution=target_res,
        blur_background=blur_bg,
        overlay_badge=overlay_badge,
        title=mixtape_title,
        genre=genre,
    )

    with col_v2:
        st.markdown("#### 🖼️ Live Cover Preview")
        if os.path.exists(styled_cover_path):
            st.image(styled_cover_path, caption=f"Thumbnail Preview ({target_res[0]}x{target_res[1]})", use_container_width=True)

    # Video Render Trigger
    st.markdown("---")
    st.markdown("### 🎥 MP4 Video Generator")

    if st.button("🎬 Render YouTube Video (.mp4)", type="primary", use_container_width=True):
        if not st.session_state.get("master_out_path") or not os.path.exists(st.session_state["master_out_path"]):
            st.error("Please generate the Master Mixtape in Tab 2 before rendering the video.")
        else:
            with st.spinner("Rendering MP4 video with FFmpeg (preset: ultrafast, yuv420p)..."):
                video_out_path = os.path.join(st.session_state["work_dir"], "mixtape_video.mp4")
                make_video_from_audio_optimized(
                    image_path=cover_image_path,
                    audio_path=st.session_state["master_out_path"],
                    output_path=video_out_path,
                    video_resolution=target_res,
                    preset="ultrafast",
                    blur_background=blur_bg,
                    overlay_badge=overlay_badge,
                    title=mixtape_title,
                    genre=genre,
                    visualizer=enable_visualizer,
                )

                with open(video_out_path, "rb") as f_v:
                    st.session_state["video_bytes"] = f_v.read()

            st.success("🎉 Video rendered successfully!")

    if st.session_state["video_bytes"] is not None:
        st.video(st.session_state["video_bytes"])
        st.download_button(
            "⬇️ Download Video (.mp4)",
            data=st.session_state["video_bytes"],
            file_name=f"{mixtape_title.replace(' ', '_').lower()}.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

    # YouTube SEO & Chapters
    st.markdown("---")
    st.markdown("### 📋 YouTube SEO & Native CUE Sheet")

    col_desc, col_cue = st.columns(2)

    with col_desc:
        st.markdown("#### 📝 YouTube Description & Timestamps (with BPM)")
        desc_val = st.session_state.get("description_text", "")
        st.text_area("YouTube Description", value=desc_val, height=260, key="txt_yt_desc")
        st.download_button(
            "⬇️ Download Description (.txt)",
            data=desc_val,
            file_name="youtube_description.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_cue:
        st.markdown("#### 💽 Native CUE Sheet (DJ CDJ / Chapter Index)")
        cue_val = st.session_state.get("cue_text", "")
        st.text_area("CUE Sheet Content", value=cue_val, height=260, key="txt_cue_sheet")
        st.download_button(
            "⬇️ Download CUE Sheet (.cue)",
            data=cue_val,
            file_name=f"{mixtape_title.replace(' ', '_').lower()}.cue",
            mime="application/x-cue",
            use_container_width=True,
        )
