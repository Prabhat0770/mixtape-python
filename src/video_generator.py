"""Cover Art Studio and dynamic FFmpeg MP4 video generator."""

import os
import subprocess
import tempfile
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Attempt to load a crisp TrueType font, falling back gracefully to default."""
    candidates = (
        ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"]
    )
    for font_name in candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def process_cover_image(
    image_path: str,
    output_path: str,
    target_resolution: Tuple[int, int] = (1280, 720),
    blur_background: bool = True,
    overlay_badge: bool = False,
    title: Optional[str] = None,
    genre: Optional[str] = None,
) -> str:
    """
    Scale, crop, and style cover art to target resolution with optional blurred background
    and sleek semi-transparent typography badge.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Cover image not found: {image_path}")

    W, H = target_resolution

    with Image.open(image_path) as src_img:
        img = src_img.convert("RGBA")

    if blur_background:
        # 1. Fill canvas with blurred, slightly darkened background
        bg = img.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(32))
        bg = ImageEnhance.Brightness(bg).enhance(0.65)

        # 2. Contain original aspect ratio inside 85% of target canvas
        max_fg_w = int(W * 0.82)
        max_fg_h = int(H * 0.82)
        fg = img.copy()
        fg.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)

        # Center foreground on blurred background
        offset_x = (W - fg.width) // 2
        offset_y = (H - fg.height) // 2

        # Create composite canvas
        composite = bg.convert("RGBA")
        composite.paste(fg, (offset_x, offset_y), mask=fg if fg.mode == "RGBA" else None)
    else:
        # Standard center-crop to target resolution
        composite = ImageOps.fit(img, target_resolution, method=Image.Resampling.LANCZOS)

    # 3. Render Sleek Semi-Transparent Typography Badge
    if overlay_badge and title:
        badge_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge_canvas)

        badge_w = min(int(W * 0.55), 650)
        badge_h = 104
        bx = 40
        by = H - badge_h - 40

        # Sleek glassmorphic card
        draw.rounded_rectangle(
            [bx, by, bx + badge_w, by + badge_h],
            radius=16,
            fill=(15, 23, 42, 215),
            outline=(255, 255, 255, 55),
            width=2,
        )

        font_title = _get_font(int(H * 0.038), bold=True)
        font_genre = _get_font(int(H * 0.022), bold=True)

        display_title = title.upper()
        # Truncate title if longer than card width
        try:
            while draw.textlength(display_title, font=font_title) > (badge_w - 50) and len(display_title) > 5:
                display_title = display_title[:-4] + "..."
        except Exception:
            if len(display_title) > 28:
                display_title = display_title[:25] + "..."

        draw.text((bx + 24, by + 16), display_title, fill=(255, 255, 255), font=font_title)

        if genre:
            genre_tag = genre.upper()
            tag_x0 = bx + 24
            tag_y0 = by + 58
            try:
                tag_w = int(draw.textlength(genre_tag, font=font_genre)) + 24
            except Exception:
                tag_w = len(genre_tag) * 11 + 24
            tag_h = 30
            draw.rounded_rectangle(
                [tag_x0, tag_y0, tag_x0 + tag_w, tag_y0 + tag_h],
                radius=8,
                fill=(239, 68, 68, 235),
            )
            draw.text((tag_x0 + 12, tag_y0 + 5), genre_tag, fill=(255, 255, 255), font=font_genre)

        composite = Image.alpha_composite(composite, badge_canvas)

    final_rgb = composite.convert("RGB")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final_rgb.save(output_path, format="JPEG", quality=93)
    return output_path


def make_video_from_audio_optimized(
    image_path: str,
    audio_path: str,
    output_path: str = "output/mixtape_video.mp4",
    video_resolution: Tuple[int, int] = (1280, 720),
    fps: int = 1,
    preset: str = "ultrafast",
    blur_background: bool = False,
    overlay_badge: bool = False,
    title: Optional[str] = None,
    genre: Optional[str] = None,
    visualizer: bool = False,
    visualizer_color: str = "0x00e5ff@0.85",
) -> str:
    """
    Combine a styled cover image and an audio file into an MP4 video using FFmpeg.
    Supports optional dynamic waveform spectrum visualizer via FFmpeg showwaves filter.

    Returns:
        The path to the generated MP4 video file.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    temp_fd, styled_img_path = tempfile.mkstemp(suffix=".jpg")
    os.close(temp_fd)

    try:
        process_cover_image(
            image_path=image_path,
            output_path=styled_img_path,
            target_resolution=video_resolution,
            blur_background=blur_background,
            overlay_badge=overlay_badge,
            title=title,
            genre=genre,
        )

        W, H = video_resolution

        if visualizer:
            # Dynamic Waveform Overlay via FFmpeg showwaves filter
            wave_fps = 24 if fps == 1 else fps
            wave_h = int(H * 0.18)
            bottom_offset = 20

            filter_complex = (
                f"[1:a]showwaves=s={W}x{wave_h}:mode=cline:colors={visualizer_color}:rate={wave_fps}[waves];"
                f"[0:v][waves]overlay=x=0:y={H - wave_h - bottom_offset}:format=auto[v]"
            )

            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                styled_img_path,
                "-i",
                audio_path,
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "1:a",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(wave_fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_path,
            ]
        else:
            # High-speed static loop
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                styled_img_path,
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_path,
            ]

        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
    finally:
        if os.path.exists(styled_img_path):
            os.remove(styled_img_path)
