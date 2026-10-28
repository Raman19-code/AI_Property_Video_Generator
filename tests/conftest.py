"""Shared helpers and fixtures for the tests."""
import io
import json
import subprocess

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from src import config
from src.validators import validate_details


def make_image_bytes(size=(1280, 720), fmt="JPEG", seed=0, mode="RGB") -> bytes:
    """A gradient image with a different colour per seed (so scenes look different)."""
    w, h = size
    x = np.linspace(0, 255, w).astype(np.int32)[None, :].repeat(h, axis=0)   # int32: no uint8 overflow
    y = np.linspace(0, 255, h).astype(np.int32)[:, None].repeat(w, axis=1)
    arr = np.stack([(x + seed * 40) % 256, y, (255 - x + seed * 70) % 256], axis=2).astype(np.uint8)
    img = Image.fromarray(arr).convert(mode)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def good_files(n=5, size=(1280, 720)):
    return [(f"photo_{i + 1}.jpg", make_image_bytes(size, seed=i)) for i in range(n)]


@pytest.fixture
def sample_data():
    return json.loads((config.DATA_DIR / "sample_property.json").read_text(encoding="utf-8"))


@pytest.fixture
def details(sample_data):
    d, res = validate_details(
        sample_data["name"], sample_data["location"], sample_data["price"], sample_data["currency"],
        sample_data["property_type"], "\n".join(sample_data["features"]),
        sample_data["contact"], sample_data["cta"],
    )
    assert d is not None, res.errors
    return d


def video_info(path) -> str:
    """Text printed by `ffmpeg -i` (codec, pixel format, size, duration)."""
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)],
                          capture_output=True, text=True)
    return proc.stderr


def extract_frame(path, seconds: float) -> Image.Image:
    proc = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-ss", str(seconds), "-i", str(path),
         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True)
    return Image.open(io.BytesIO(proc.stdout)).convert("RGB")
