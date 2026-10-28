"""Turns images + a VideoScript into an MP4.

Pipeline (one line each):
  image  -> centre-crop to the video size (ImageOps.fit)
  scene  -> text panel drawn with Pillow (so no ImageMagick/font problems on Windows)
  clip   -> slow zoom ("Ken Burns") + text overlay, built frame by frame
  scenes -> overlapped by 0.8 s with a cross-fade
  export -> H.264 (libx264) + yuv420p, which plays in every browser
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from src import config
from src.script_generator import Scene, VideoScript

ProgressCallback = Callable[[float, str], None]


class VideoGenerationError(Exception):
    """Raised with a short, user-friendly message when the video cannot be made."""


# --------------------------------------------------------------------------- #
# Fonts and text layout
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=128)
def load_font(bold: bool, size: int) -> ImageFont.ImageFont:
    """Bundled DejaVu font (works on every PC). Falls back to Pillow's default font."""
    path = config.FONT_BOLD if bold else config.FONT_REGULAR
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # very old Pillow
            return ImageFont.load_default()


def _line_height(font: ImageFont.ImageFont) -> int:
    box = font.getbbox("Hg")
    return int((box[3] - box[1]) * 1.35) or 12


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Word-wrap `text` so each line is at most `max_width` pixels. Very long words are split."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        while font.getlength(current) > max_width and len(current) > 1:   # one huge word
            cut = len(current) - 1
            while cut > 1 and font.getlength(current[:cut]) > max_width:
                cut -= 1
            lines.append(current[:cut])
            current = current[cut:]
    if current:
        lines.append(current)
    return lines


def _ellipsize(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


def fit_text(text: str, bold: bool, start: int, minimum: int, max_width: int, max_lines: int):
    """Shrink the font until the text fits in `max_lines`; as a last resort cut with '…'."""
    start, minimum = max(int(start), 10), max(int(minimum), 10)
    for size in range(start, minimum - 1, -2):
        font = load_font(bold, size)
        lines = wrap_text(text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = load_font(bold, minimum)
    lines = wrap_text(text, font, max_width)[:max_lines]
    if lines:
        lines[-1] = _ellipsize(lines[-1] + " …", font, max_width)
    return font, lines


def _draw_text(layer: Image.Image, xy, text: str, font, color, anchor: str) -> None:
    """Draw anti-aliased text with correct transparency (no dark fringes)."""
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor=anchor)
    solid = Image.new("RGBA", layer.size, tuple(color) + (0,))
    solid.putalpha(mask)
    layer.alpha_composite(solid)


# --------------------------------------------------------------------------- #
# Overlay (text panel) for one scene
# --------------------------------------------------------------------------- #

_START_SIZES = {  # (title, subtitle) starting font sizes per scene kind, for a 1280-wide frame
    "hook": (68, 40),
    "intro": (60, 54),
    "feature": (60, 40),
    "card": (64, 40),
    "closing": (72, 48),
}


def build_overlay(scene: Scene, size: tuple[int, int]) -> Image.Image:
    """Return an RGBA image (same size as the video) holding the dark panel + captions."""
    W, H = size
    landscape = W >= H
    u = W / (1280 if landscape else 720)          # scale factor so text looks the same in both formats
    margin = int(72 * u)
    max_w = W - 2 * margin
    centered = scene.kind == "closing"
    title_start, sub_start = _START_SIZES.get(scene.kind, (64, 40))

    # ---- 1. measure every text block ------------------------------------------------
    blocks = []  # (kind, lines, font, color, gap_after)
    if scene.label:
        f, ls = fit_text(scene.label.upper(), True, 28 * u, 18 * u, max_w, 1)
        blocks.append(("text", ls, f, config.COLOR_GOLD, int(14 * u)))
    if scene.title:
        f, ls = fit_text(scene.title, True, title_start * u, 34 * u, max_w, 2 if landscape else 3)
        blocks.append(("text", ls, f, config.COLOR_WHITE, int(16 * u)))
    if scene.subtitle:
        f, ls = fit_text(scene.subtitle, True, sub_start * u, 24 * u, max_w, 2)
        blocks.append(("text", ls, f, config.COLOR_GOLD, int(12 * u)))
    for line in scene.lines:
        f, ls = fit_text(line, False, 44 * u, 26 * u, max_w - int(44 * u), 2)
        blocks.append(("bullet", ls, f, config.COLOR_WHITE, int(14 * u)))

    bar_h, bar_gap = int(6 * u), int(22 * u)
    total_h = bar_h + bar_gap
    for _, ls, f, _, gap in blocks:
        total_h += len(ls) * _line_height(f) + gap

    # ---- 2. dark panel behind the text ------------------------------------------
    bottom_margin = margin if landscape else int(margin * 1.8)
    if centered:
        top = (H - total_h) // 2
        alpha = np.full((H, W), int(0.70 * 255), dtype=np.uint8)
    else:
        top = H - bottom_margin - total_h
        fade_start = max(0, top - int(170 * u))
        ys = np.arange(H, dtype=np.float32)
        ramp = np.clip((ys - fade_start) / max(1, top - fade_start), 0, 1) ** 1.3
        alpha = np.repeat((ramp * 0.88 * 255).astype(np.uint8)[:, None], W, axis=1)
    panel = np.zeros((H, W, 4), dtype=np.uint8)
    panel[..., :3] = config.COLOR_PANEL
    panel[..., 3] = alpha
    layer = Image.fromarray(panel)   # H x W x 4 uint8 -> RGBA

    # ---- 3. draw accent bar + text ------------------------------------------------
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    bar_w = int(96 * u)
    bar_x = (W - bar_w) // 2 if centered else margin
    draw.rectangle([bar_x, top, bar_x + bar_w, top + bar_h], fill=config.COLOR_GOLD + (255,))

    y = top + bar_h + bar_gap
    for kind, ls, font, color, gap in blocks:
        lh = _line_height(font)
        for text in ls:
            if kind == "bullet":
                s = int(14 * u)
                cy = y + lh // 2
                draw.rectangle([margin, cy - s // 2, margin + s, cy + s // 2], fill=config.COLOR_GOLD + (255,))
                _draw_text(text_layer, (margin + int(44 * u), y), text, font, color, "la")
            elif centered:
                _draw_text(text_layer, (W // 2, y), text, font, color, "ma")
            else:
                _draw_text(text_layer, (margin, y), text, font, color, "la")
            y += lh
        y += gap

    return Image.alpha_composite(layer, text_layer)


# --------------------------------------------------------------------------- #
# One scene -> one MoviePy clip
# --------------------------------------------------------------------------- #


def _make_scene_clip(img: Image.Image, scene: Scene, size: tuple[int, int], duration: float, reverse_zoom: bool):
    from moviepy import VideoClip

    W, H = size
    zoom = config.ZOOM_AMOUNT
    pad = 1 + zoom
    base = ImageOps.fit(img, (int(W * pad), int(H * pad)), Image.LANCZOS)   # centre-crop, no stretching
    bw, bh = base.size

    overlay = build_overlay(scene, size)
    overlay_rgb, overlay_mask = overlay.convert("RGB"), overlay.getchannel("A")

    def make_frame(t: float) -> np.ndarray:
        p = min(max(t / duration, 0.0), 1.0)
        if reverse_zoom:
            p = 1.0 - p
        scale = 1 + zoom * (1 - p)                     # window shrinks => slow zoom-in
        w, h = min(W * scale, bw), min(H * scale, bh)   # never larger than the image (float rounding)
        x0, y0 = (bw - w) / 2, (bh - h) / 2
        frame = base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
        frame.paste(overlay_rgb, (0, 0), overlay_mask)
        return np.asarray(frame)

    return VideoClip(make_frame, duration=duration)


# --------------------------------------------------------------------------- #
# Progress reporting while FFmpeg encodes
# --------------------------------------------------------------------------- #


def _make_logger(callback: ProgressCallback | None, start: float, span: float):
    if callback is None:
        return None
    try:
        import proglog
    except ImportError:   # MoviePy always installs it, but stay safe
        return None

    class _Logger(proglog.ProgressBarLogger):
        _last = -1.0

        def bars_callback(self, bar, attr, value, old_value=None):
            if attr != "index":
                return
            total = self.bars[bar].get("total") or 0
            if total:
                frac = min(max(value / total, 0.0), 1.0)
                if frac - self._last >= 0.01 or frac >= 1.0:   # update the UI at most ~100 times
                    self._last = frac
                    callback(start + span * frac, "Encoding video (this takes a little while)...")

    return _Logger()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return (slug or "property")[:max_len].strip("_") or "property"


def prune_old_outputs(folder: Path = config.OUTPUT_DIR, keep: int = config.KEEP_LAST_OUTPUTS) -> None:
    """Delete the oldest generated files (sample_* files are never deleted)."""
    try:
        files = [p for p in folder.glob("*") if p.is_file() and not p.name.startswith("sample_")]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[keep * 2:]:   # each video has a script file too
            old.unlink(missing_ok=True)
    except OSError:
        pass   # cleaning is a nicety, never a reason to fail


def generate_video(
    images: Sequence[Image.Image],
    script: VideoScript,
    output_path: str | os.PathLike,
    aspect: tuple[int, int] = config.ASPECT_RATIOS[config.DEFAULT_ASPECT],
    progress: ProgressCallback | None = None,
    music: bool = False,
) -> Path:
    """Render the MP4 (optionally with a generated background-music track). Raises VideoGenerationError (friendly message) on any failure."""
    from moviepy import CompositeVideoClip, vfx

    report = progress or (lambda frac, msg: None)
    n = len(script.scenes)
    if len(images) != n:
        raise VideoGenerationError(f"Scene/image mismatch: {n} scenes but {len(images)} images.")
    W, H = aspect
    if W % 2 or H % 2 or W < 320 or H < 320:
        raise VideoGenerationError("Video size must use even numbers and be at least 320 pixels.")

    out = Path(output_path)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise VideoGenerationError(f"Cannot create the output folder '{out.parent}'. Check permissions.") from exc
    tmp = out.with_name(f"{out.stem}.part{out.suffix or '.mp4'}")

    clips, final, audio = [], None, None
    wav = out.with_name(f"{out.stem}.part.wav")
    try:
        report(0.02, "Preparing scenes...")
        step = script.scene_seconds
        for i, (img, scene) in enumerate(zip(images, script.scenes)):
            clip = _make_scene_clip(img, scene, (W, H), step + config.FADE_SECONDS, reverse_zoom=bool(i % 2))
            clip = clip.with_start(i * step)
            if i > 0:
                clip = clip.with_effects([vfx.CrossFadeIn(config.FADE_SECONDS)])
            clips.append(clip)
            report(0.02 + 0.08 * (i + 1) / n, f"Prepared scene {i + 1} of {n}")

        final = CompositeVideoClip(clips, size=(W, H))
        if music:
            from moviepy import AudioFileClip, afx
            from .music import synthesize_music
            synthesize_music(final.duration, wav)
            audio = AudioFileClip(str(wav)).with_effects(
                [afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
            final = final.with_audio(audio)
        report(0.10, "Encoding video (this takes a little while)...")
        final.write_videofile(
            str(tmp),
            fps=config.FPS,
            codec="libx264",
            audio=bool(music),
            audio_codec="aac",
            preset="veryfast",
            pixel_format="yuv420p",
            ffmpeg_params=["-crf", "22", "-movflags", "+faststart"],
            logger=_make_logger(progress, 0.10, 0.88),
        )
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise VideoGenerationError("The encoder finished but produced an empty file.")
        os.replace(tmp, out)   # only publish the file when it is complete
        report(1.0, "Done")
        return out
    except VideoGenerationError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001 - we want to turn *everything* into a friendly message
        tmp.unlink(missing_ok=True)
        text = str(exc).lower()
        if isinstance(exc, PermissionError):
            hint = "Windows blocked writing the file. Close any player that has the video open, or choose another folder."
        elif "no space" in text:
            hint = "Your disk is full. Free some space and try again."
        elif isinstance(exc, MemoryError):
            hint = "Not enough memory. Use fewer or smaller images, or the 16:9 format."
        else:
            hint = "Try fewer or smaller images. If it keeps failing, see the Troubleshooting section of the README."
        raise VideoGenerationError(f"Video export failed ({type(exc).__name__}). {hint}") from exc
    finally:
        if audio is not None:
            audio.close()
        wav.unlink(missing_ok=True)
        for c in clips:
            c.close()
        if final is not None:
            final.close()
