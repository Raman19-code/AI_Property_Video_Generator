# AI / Model / API / Library Disclosure

## AI models and external APIs used by the application at run time

**By default none.** The default script is rule-based and works offline. One optional feature, "AI voice-over polish" (off by default, `src/llm_rewriter.py`), calls an LLM API (Google Gemini or Anthropic Claude) **only if the user switches it on and types their own API key**. The key is not saved. Only the property facts typed in the form are sent (never the photos). Each AI sentence is rejected if it adds a number, a word outside the user's facts, or drops a fact, and on-screen captions are never rewritten by the AI.

| Question | Answer |
|---|---|
| Is a large language model used? | Only in the optional AI polish, never by default |
| Are any API keys needed? | No, except for the optional AI polish (user's own key, typed in the app or in the `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` environment variable). No key is in the source code |
| Does the app send data to the internet? | Not by default. With AI polish on, the typed property facts and one sentence per scene are sent to the chosen provider. Photos and property details stay on your computer. Streamlit's anonymous usage statistics are switched off in `.streamlit/config.toml` |
| Narration / text-to-speech? | Not implemented. The voice-over script is generated as text only |
| Background music? | Optional checkbox (off by default). The tune is synthesised from sine waves by `src/music.py`, so no third-party music or licence is involved |

### How the "AI" part works
The script and captions are produced by **deterministic, template-based natural-language generation** with a
**grounding check** (see `src/script_generator.py`):

1. Fixed sentence templates are filled with the user's validated facts only.
2. `check_grounding()` re-reads every generated line and rejects it if it contains a number or a word that is
   neither in the user's facts nor in the template vocabulary.
3. Automated tests also check that the templates contain no marketing superlatives (for example "luxury", "stunning").

This was chosen on purpose: it makes it impossible for the generator to invent amenities, prices or distances.

## Libraries (all installed from PyPI by `pip install -r requirements.txt`)

| Library | Used for | Licence |
|---|---|---|
| Streamlit | Web user interface, video preview, download buttons | Apache-2.0 |
| MoviePy 2.x | Assembling scenes, cross-fades, MP4 export | MIT |
| Pillow | Image validation, centre-crop, drawing text overlays | HPND (permissive) |
| NumPy | Pixel arithmetic for the text panel and video frames | BSD-3-Clause |
| imageio / imageio-ffmpeg | Pulls in an FFmpeg executable used by MoviePy | BSD-2-Clause (wrapper) |
| FFmpeg (with libx264) | H.264 video encoding. Downloaded as a binary by imageio-ffmpeg | FFmpeg builds that include libx264 are GPL-licensed. Fine for this assignment; check the licence before commercial redistribution |
| proglog | Progress reporting from MoviePy | MIT |
| pytest | Automated tests (development only) | MIT |

## Assets

| Asset | Source | Licence |
|---|---|---|
| `assets/sample_images/*.jpg` | Drawn by `scripts/make_sample_images.py` using Pillow. They are flat illustrations, not photographs, and show no real property | Created for this project |
| `assets/fonts/DejaVuSans*.ttf` | DejaVu Fonts project | Free licence, see `assets/fonts/DEJAVU_LICENSE.txt` |
| `data/sample_property.json` | Written for this project. The property, address, phone number and email are **fictional** (`example.com`) | Created for this project |

No copyrighted photos, music or logos are included.

## Development assistance
The source code was written and tested with the help of an AI coding assistant (Claude, by Anthropic).
*(Keep or edit this line according to your institution's rules about disclosing AI assistance.)*
