# AI / Model / API / Library Disclosure

## AI models and external APIs used by the application at run time

**None.** The application does not call any AI model, LLM, text-to-speech service, or web API while it runs.

| Question | Answer |
|---|---|
| Is a large language model used? | No |
| Are any API keys needed? | No. There is no `.env` file and no secret in the source code |
| Does the app send data to the internet? | No. Photos and property details stay on your computer. Streamlit's anonymous usage statistics are switched off in `.streamlit/config.toml` |
| Narration / text-to-speech? | Not implemented. The voice-over script is generated as text only |
| Background music? | Not used, so there are no music licensing questions |

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
