"""Original background music, synthesised with NumPy (no download, no licence issue).

A soft, slow chord pad (C major 7 -> A minor -> F major -> G major). It is created
from sine waves, so the audio is ours to use freely.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
# chord notes in Hz: Cmaj7, Am7, Fmaj7, G6
_CHORDS = [
    (130.81, 164.81, 196.00, 246.94),
    (110.00, 164.81, 196.00, 261.63),
    (87.31, 130.81, 174.61, 220.00),
    (98.00, 146.83, 196.00, 246.94),
]


def synthesize_music(duration: float, path: str | Path, volume: float = 0.5) -> Path:
    """Write a mono 16-bit WAV of `duration` seconds to `path`."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    chord_len = 4.0
    out = np.zeros(n)
    for k, chord in enumerate(_CHORDS * (int(duration // (chord_len * len(_CHORDS))) + 2)):
        start = k * chord_len
        if start >= duration:
            break
        i0, i1 = int(start * SAMPLE_RATE), min(n, int((start + chord_len + 1.0) * SAMPLE_RATE))
        seg_t = t[i0:i1] - start
        env = np.minimum(1.0, seg_t / 1.0) * np.clip((chord_len + 1.0 - seg_t) / 1.0, 0, 1)
        tone = sum(np.sin(2 * np.pi * f * seg_t) + 0.3 * np.sin(4 * np.pi * f * seg_t) for f in chord)
        out[i0:i1] += env * tone
    out *= 1 + 0.08 * np.sin(2 * np.pi * 0.25 * t)       # gentle shimmer
    peak = np.max(np.abs(out)) or 1.0
    pcm = (out / peak * volume * 32767).astype(np.int16)
    path = Path(path)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return path
