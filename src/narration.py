"""Text-to-speech narration using gTTS (Google Text-to-Speech).

Generates one MP3 per scene voice-over line, then combines them into a single
audio track timed to match each scene's position in the video.

Requirements: pip install gTTS
Internet is needed (gTTS calls Google Translate's free TTS endpoint).
Uses MoviePy for audio combining (already installed), so no extra dependency like pydub.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from src.script_generator import VideoScript


def generate_narration(
    script: VideoScript,
    output_path: str | Path,
    lang: str = "en",
) -> Path:
    """Create a WAV file with spoken narration timed to each scene.

    Each scene's voice-over is spoken starting at the scene's start time.
    Silence fills the gaps. Returns the path to the combined WAV file.
    """
    from gtts import gTTS
    from moviepy import AudioFileClip, CompositeAudioClip, AudioClip
    import numpy as np

    out = Path(output_path)
    step = script.scene_seconds
    total = script.total_seconds

    # generate TTS mp3 for each scene into temp files
    temp_files = []
    audio_clips = []

    try:
        for scene in script.scenes:
            text = (scene.voiceover or "").strip()
            if not text:
                continue

            # save TTS to a temp mp3 file
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            temp_files.append(tmp.name)

            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(tmp.name)

            # load as MoviePy audio clip
            clip = AudioFileClip(tmp.name)
            start_time = scene.index * step

            # trim if speech is longer than scene duration
            scene_duration = step + 0.8  # scene_seconds + fade
            if clip.duration > scene_duration:
                clip = clip.subclipped(0, scene_duration)

            clip = clip.with_start(start_time)
            audio_clips.append(clip)

        if not audio_clips:
            # no voiceover text, create silence
            silence = AudioClip(lambda t: np.array([[0.0]]), duration=total, fps=44100)
            silence.write_audiofile(str(out), fps=44100, logger=None)
            silence.close()
            return out

        combined = CompositeAudioClip(audio_clips)
        combined.write_audiofile(str(out), fps=44100, logger=None)

        # close clips
        for c in audio_clips:
            c.close()
        combined.close()

    finally:
        # clean up temp mp3 files
        import os
        for f in temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass

    return out
