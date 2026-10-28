"""Video generation tests. The `slow` ones render real MP4 files."""
import re

import numpy as np
import pytest
from PIL import Image

from src import config
from src.script_generator import Scene, generate_script
from src.validators import load_and_validate_images, validate_details
from src.video_generator import (VideoGenerationError, build_overlay, fit_text, generate_video,
                                 load_font, slugify, wrap_text)
from tests.conftest import extract_frame, good_files, video_info


def _details(**over):
    args = dict(name="Maple Grove", location="Sector 9", price="85,00,000", currency="INR",
                property_type="3 BHK Apartment", features_raw="3 bedrooms\n2 bathrooms\nBalcony\nParking\nSecurity",
                contact="+91 90000 00000", cta="Call us today")
    args.update(over)
    d, res = validate_details(**args)
    assert d is not None, res.errors
    return d


def _images(n, size=(1280, 720)):
    imgs, res = load_and_validate_images(good_files(n, size))
    assert res.ok, res.errors
    return imgs


# ------------------------------------------------------------------ overlay / layout (fast)
@pytest.mark.parametrize("size", [(1280, 720), (720, 1280)])
def test_long_name_overlay_stays_inside_margins(size):
    W, H = size
    long_name = "The Extraordinarily Long Named Residency of the Grand Sunrise Gardens Estate"[: config.MAX_NAME]
    scene = Scene(index=0, kind="hook", image_index=0, title=long_name, subtitle="L" * config.MAX_LOCATION)
    overlay = build_overlay(scene, size).convert("RGB")
    arr = np.asarray(overlay).astype(int)
    u = W / (1280 if W >= H else 720)
    margin = int(72 * u)
    right_strip = arr[:, W - margin + 6:, :]
    assert right_strip.sum(axis=2).max() < 300      # no bright text pixels in the right margin


def test_long_feature_lines_are_shrunk_or_wrapped_not_overflowing():
    font, lines = fit_text("B" * config.MAX_FEATURE, False, 44, 26, 900, 2)
    assert 1 <= len(lines) <= 2 and all(font.getlength(l) <= 900 for l in lines)


def test_single_giant_word_is_split():
    font = load_font(True, 40)
    lines = wrap_text("W" * 200, font, 500)
    assert len(lines) > 1 and all(font.getlength(l) <= 500 for l in lines)


def test_slugify_is_filesystem_safe():
    assert slugify("Maple Grove / Residency: 3BHK!") == "maple_grove_residency_3bhk"
    assert slugify("???") == "property"


# ------------------------------------------------------------------ failures (fast)
def test_image_scene_mismatch_is_friendly_error(tmp_path):
    script = generate_script(_details(), 5)
    with pytest.raises(VideoGenerationError, match="mismatch"):
        generate_video(_images(4), script, tmp_path / "x.mp4")


def test_unwritable_output_folder_is_friendly_error(tmp_path):
    blocker = tmp_path / "a_file"
    blocker.write_text("x")
    script = generate_script(_details(), 4)
    with pytest.raises(VideoGenerationError, match="output folder"):
        generate_video(_images(4), script, blocker / "sub" / "out.mp4")


def test_invalid_video_size_rejected(tmp_path):
    script = generate_script(_details(), 4)
    with pytest.raises(VideoGenerationError, match="even"):
        generate_video(_images(4), script, tmp_path / "x.mp4", aspect=(1281, 720))


def test_encoder_failure_becomes_friendly_error_and_leaves_no_files(tmp_path, monkeypatch):
    from moviepy import CompositeVideoClip

    def boom(self, *a, **k):
        raise OSError("No space left on device")

    monkeypatch.setattr(CompositeVideoClip, "write_videofile", boom)
    script = generate_script(_details(), 4)
    out = tmp_path / "out.mp4"
    with pytest.raises(VideoGenerationError) as err:
        generate_video(_images(4), script, out)
    assert "disk is full" in str(err.value)
    assert not out.exists() and list(tmp_path.glob("*.part*")) == []


# ------------------------------------------------------------------ real renders (slow)
@pytest.mark.slow
def test_landscape_8_images_end_to_end(tmp_path):
    d = _details()
    imgs = _images(8)
    script = generate_script(d, 8)
    calls = []
    out = generate_video(imgs, script, tmp_path / "land.mp4", progress=lambda f, m: calls.append(f))

    assert out.exists() and out.stat().st_size > 50_000
    info = video_info(out)
    assert "Video: h264" in info and "yuv420p" in info and "1280x720" in info   # plays in browsers
    assert "Audio:" not in info                                                  # narration is optional
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    seconds = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    assert 20 <= seconds <= 40 and abs(seconds - script.total_seconds) < 1.0

    assert calls and calls[-1] == 1.0 and calls == sorted(calls)                 # progress is monotonic
    assert list(tmp_path.glob("*.part*")) == []                                  # no temp files left

    # Content checks: first scene shows the property name panel, last scene shows the enquiry prompt
    first, last = extract_frame(out, 1.0), extract_frame(out, seconds - 0.3)
    assert np.asarray(first).std() > 5 and not np.array_equal(np.asarray(first), np.asarray(last))
    arr = np.asarray(last).astype(int)
    white = (arr.min(axis=2) > 235)
    centre_band = white[int(config.ASPECT_RATIOS[config.DEFAULT_ASPECT][1] * 0.3):int(720 * 0.7), :]
    assert centre_band.sum() > 800                                              # big white CTA text present
    gold = (arr[..., 0] > 200) & (arr[..., 1] > 150) & (arr[..., 2] < 140)
    assert gold.sum() > 300                                                      # contact line in gold present


@pytest.mark.slow
def test_vertical_format_with_mixed_aspect_ratios(tmp_path):
    files = [("a.jpg", good_files(1, (1600, 900))[0][1]), ("b.jpg", good_files(1, (900, 1600))[0][1]),
             ("c.jpg", good_files(1, (1200, 1200))[0][1]), ("d.jpg", good_files(1, (2400, 1000))[0][1])]
    imgs, res = load_and_validate_images(files)
    assert res.ok
    script = generate_script(_details(contact=""), 4)                            # also: no contact details
    out = generate_video(imgs, script, tmp_path / "vert.mp4", aspect=config.ASPECT_RATIOS["Vertical 9:16 (720x1280)"])
    info = video_info(out)
    assert "720x1280" in info and "h264" in info
    last = extract_frame(out, 19.5)
    assert last.size == (720, 1280)


def test_music_synth_is_valid_wav(tmp_path):
    import wave
    from src.music import synthesize_music
    p = synthesize_music(5.0, tmp_path / "m.wav")
    with wave.open(str(p)) as w:
        assert w.getnframes() == 5 * w.getframerate() and w.getnchannels() == 1
    with pytest.raises(ValueError):
        synthesize_music(0, tmp_path / "x.wav")


@pytest.mark.slow
def test_video_with_music_has_aac_audio_and_same_length(tmp_path):
    d = _details()
    script = generate_script(d, 4)
    out = generate_video(_images(4), script, tmp_path / "m.mp4", music=True)
    info = video_info(out)
    assert "Audio: aac" in info and "Video: h264" in info and "yuv420p" in info
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    seconds = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    assert abs(seconds - script.total_seconds) < 1.0
    assert list(tmp_path.glob("*.part*")) == []                  # temp wav and mp4 cleaned up


@pytest.mark.slow
def test_users_own_short_audio_is_looped_and_bad_audio_is_friendly(tmp_path):
    from src.music import synthesize_music
    short = synthesize_music(3.0, tmp_path / "short.wav")           # shorter than the video -> must loop
    d = _details()
    script = generate_script(d, 4)
    out = generate_video(_images(4), script, tmp_path / "own.mp4", audio_file=short)
    info = video_info(out)
    assert "Audio: aac" in info
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    assert abs(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) - script.total_seconds) < 1.0

    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"this is not audio")
    with pytest.raises(VideoGenerationError, match="audio file"):
        generate_video(_images(4), script, tmp_path / "bad.mp4", audio_file=bad)
    assert list(tmp_path.glob("*.part*")) == [] and not (tmp_path / "bad.mp4").exists()
