# AI Property Video Generator

> Automatically generate professional real-estate promotional videos from property details and photos — in under a minute.

**Built with:** Python 3.13 | Streamlit | MoviePy 2.x | Pillow | NumPy | gTTS | Google Gemini / Anthropic Claude (optional)

![sample frame](docs/sample_frame.png)

---

## Highlights

- **Zero hallucination guarantee** — Script uses only the facts you type. A grounding validator rejects any AI-generated sentence that adds new information.
- **Multi-language narration** — Optional text-to-speech in 10 languages (English, Hindi, Spanish, French, Arabic, Portuguese, German, Japanese, Chinese, Korean) using Google TTS.
- **QR code in closing scene** — Auto-generates a scannable QR code from contact details, embedded in the final scene for instant enquiry.
- **Background music** — Optional original synthesised music, or upload your own MP3/WAV/M4A track.
- **AI voice-over polish** — Optional LLM integration (Gemini / Claude) rephrases the voice-over to sound natural, with strict fact-checking on every sentence.
- **Smart photo-feature matching** — Label your photos (e.g. "Kitchen") and features auto-match to the right image.
- **109 automated tests** — Validators, script generation, grounding checks, video rendering, QR code, and edge cases.
- **Works offline by default** — No API key or internet required for the core workflow.

---

## Architecture

```
                          +------------------+
                          |     app.py       |  Streamlit UI
                          |  (User Interface)|  Form + Upload + Preview + Download
                          +--------+---------+
                                   |
                    +--------------+--------------+
                    |                             |
           +--------v--------+          +---------v---------+
           |  validators.py  |          | script_generator.py|
           |  Input & Image  |          | Template NLG +     |
           |  Validation     |          | Grounding Check    |
           +-----------------+          +---------+----------+
                                                  |
                                     +------------+------------+
                                     |                         |
                              +------v------+          +-------v--------+
                              | llm_rewriter|          | narration.py   |
                              | AI Polish   |          | Text-to-Speech |
                              | (Optional)  |          | via gTTS       |
                              +------+------+          | (Optional)     |
                                     |                 +-------+--------+
                                     |                         |
                              +------v-------------------------v------+
                              |        video_generator.py              |
                              |  Image Processing + Ken Burns Zoom     |
                              |  Text Overlay (Pillow) + Crossfade     |
                              |  Audio Mixing (Narration + Music)      |
                              |  H.264 MP4 Export via FFmpeg            |
                              +----------------------------------------+
                                               |
                                        +------v------+
                                        |  Output MP4  |
                                        |  + Script    |
                                        +-------------+
```

---

## Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.13** | Core language |
| **Streamlit** | Interactive web UI with live preview |
| **MoviePy 2.x** | Video editing — scene assembly, crossfades, audio mixing |
| **Pillow (PIL)** | Image processing, text overlay rendering |
| **NumPy** | Pixel-level operations for Ken Burns zoom effect |
| **gTTS** | Google Text-to-Speech for multi-language narration (free) |
| **qrcode** | QR code generation for closing scene contact card |
| **FFmpeg** | H.264 video encoding (via imageio-ffmpeg) |
| **Google Gemini / Claude API** | Optional AI voice-over polish |
| **pytest** | 109 automated tests |

---

## Features

### Core Pipeline
- Accept property details: name, location, price (multi-currency), type, features, contact, CTA
- Accept 4–8 images (JPG/PNG) with optional labels
- Generate a fact-grounded promotional script using template-based NLG
- Render scenes with Ken Burns zoom effect and Pillow text overlays
- Crossfade transitions between scenes (0.8s overlap)
- Export browser-compatible H.264 MP4 (yuv420p)
- In-app preview + download (MP4 and script)

### Audio Features
- **Multi-language narration** — gTTS converts voice-over to speech in 10 languages (EN, HI, ES, FR, AR, PT, DE, JA, ZH, KO), timed to each scene
- **Background music** — Original synthesised music from sine waves (no licensing issues)
- **Custom audio** — Upload your own MP3/WAV/M4A (max 15 MB, looped/trimmed to fit)
- **Smart mixing** — When both narration and music are active, music volume auto-lowers to 30%

### Visual Enhancements
- **QR code overlay** — Auto-generated QR code from contact details, embedded in the closing scene (top-right corner)
- **Scannable by any phone** — QR encodes contact info (phone, email, CTA) for instant enquiry

### AI Features
- **Grounding validation** — Every generated sentence is verified against user input; unknown words/numbers are rejected
- **LLM polish (optional)** — Gemini or Claude rephrases voice-over for natural flow
- **Strict safety** — AI-polished sentences that add, remove, or alter facts are discarded; originals are kept
- **No API key required** — AI features are optional; core pipeline works fully offline

### Validation & Error Handling
- Required field validation with clear error messages
- Image format verification (real file type, not just extension)
- Corrupt/truncated image detection
- File size and dimension limits
- EXIF rotation correction
- Graceful fallbacks for all optional features

---

## Quick Start

### Windows (one-click)

1. Install [Python 3.10+](https://www.python.org/downloads/) — tick **"Add python.exe to PATH"**
2. Clone this repository
3. **Double-click `run.bat`** — it creates a virtual environment, installs dependencies, and opens the app

### Manual Setup

```bash
git clone https://github.com/Raman19-code/AI_Property_Video_Generator.git
cd AI_Property_Video_Generator
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

### Command-Line Generation

```bash
python scripts/generate_sample_video.py
```

---

## How It Works

### Script Generation (Zero Hallucination)

The script generator uses **deterministic template-based Natural Language Generation**:

1. Fixed sentence templates are filled with the user's validated facts only
2. `check_grounding()` re-reads every generated line and rejects anything containing a number or word not present in the user's input or template vocabulary
3. Automated tests verify that templates contain no marketing superlatives ("luxury", "stunning", etc.)

**Why templates instead of pure LLM?** A real-estate video must never promise something untrue. Templates guarantee factual accuracy, run offline, cost nothing, and always work. The grounding check also serves as a safety net for the optional LLM polish — any AI output that adds new claims is rejected.

### Scene Planning

| Scene | Content | Image |
|---|---|---|
| Hook | Property name + location | Photo 1 |
| Intro | Property type + price | Photo 2 |
| Features | Up to 3 features per photo (matched by labels) | Photos 3–N |
| Closing | Call-to-action + contact | Last photo |

### Feature-to-Photo Matching

The app cannot see photo content, so matching is rule-based:
- User labels each photo (e.g. "Kitchen", "Bedroom")
- `match_score()` uses lowercase + plural stemming + word overlap
- "Kitchen" label matches "Modular kitchen" feature
- Unmatched features go to unlabelled photos only
- Without labels, features are placed in upload order

### Audio Pipeline

```
Voice-over text (per scene)
        |
   gTTS  --> MP3 per scene --> MoviePy AudioFileClip
        |                           |
        +---> CompositeAudioClip (positioned at scene start times)
        |
  Background music (optional) --> volume lowered to 30% if narration active
        |
        +---> Final audio track --> mixed into MP4
```

---

## Project Structure

```
app.py                        Streamlit UI (form, preview, download)
run.bat                       One-click Windows launcher
requirements.txt              Python dependencies

src/
  config.py                   All settings (limits, sizes, timings, colours)
  validators.py               Input validation (text fields + images)
  script_generator.py         Template NLG + scene planning + grounding check
  narration.py                Text-to-speech using gTTS + MoviePy
  music.py                    Synthesised background music (sine waves)
  llm_rewriter.py             Optional AI polish (Gemini / Claude) + safety checks
  video_generator.py          Image processing, zoom, crossfade, audio mixing, MP4 export

tests/
  test_validators.py          40 tests — form fields and image validation
  test_script_generator.py    39 tests — scene structure, grounding, matching
  test_video_generator.py     17 tests — text layout, rendering, QR code, narration lang, MP4 export
  test_llm_rewriter.py         6 tests — AI polish safety (fake LLM functions)
  test_app_ui.py               4 tests — headless Streamlit (full generate flow)
  conftest.py                 Shared fixtures

data/sample_property.json     Fictional demo property with photo labels
assets/sample_images/         7 synthetic illustrations (not real photos)
assets/fonts/                 DejaVu Sans (bundled) + licence
outputs/                      Generated videos (sample included)
scripts/                      Utility scripts (image generation, sample video)
docs/                         Documentation assets

DISCLOSURE.md                 AI/API/library disclosure
TEST_RESULTS.md               Actual test results (103 passed, 0 failed)
DEMO_SCRIPT.md                Demo walkthrough and Q&A prep
INTERVIEW_PREP.md             Interview preparation guide
```

---

## Testing

```bash
# Run all 109 tests (~2 minutes, includes real video renders)
python -m pytest tests -q

# Fast tests only (a few seconds)
python -m pytest tests -q -m "not slow"
```

**Result: 109 passed, 0 failed**

| Test File | Count | Coverage |
|---|---|---|
| `test_validators.py` | 40 | Form fields, image format/size/corruption, EXIF rotation |
| `test_script_generator.py` | 39 | Scene structure, grounding check, feature matching, video length |
| `test_video_generator.py` | 17 | Text overlay, Ken Burns zoom, crossfade, QR code, narration language, MP4 export |
| `test_llm_rewriter.py` | 6 | AI polish safety — invented words/numbers rejected, fallback on error |
| `test_app_ui.py` | 4 | Headless Streamlit UI, full generate-and-download flow |

See [`TEST_RESULTS.md`](TEST_RESULTS.md) for detailed results.

---

## Configuration

All configurable values are centralised in `src/config.py`:

| Setting | Default | Description |
|---|---|---|
| `MIN_IMAGES` / `MAX_IMAGES` | 4 / 8 | Accepted photo count |
| `FPS` | 24 | Video frame rate |
| `MIN_SCENE_SECONDS` / `MAX_SCENE_SECONDS` | 4.0 / 5.0 | Duration per scene |
| `FADE_SECONDS` | 0.8 | Crossfade overlap |
| `ZOOM_AMOUNT` | 0.06 | Ken Burns zoom (6%) |
| `ASPECT_RATIOS` | 16:9, 9:16 | Landscape and vertical |
| `CURRENCIES` | INR, USD, EUR, GBP, AED | Supported currencies |
| `NARRATION_LANGUAGES` | 10 languages | Narration language options |
| `QR_SIZE` | 180 px | QR code size (scales with resolution) |

---

## Limitations

- Captions support Latin, Cyrillic and Greek scripts (DejaVu Sans). Hindi/Devanagari glyphs may not render.
- Photo content is not recognised — feature matching depends on user-provided labels.
- CPU-only rendering: ~30–60 seconds for a 30-second video on a standard laptop.
- gTTS narration requires internet (Google TTS endpoint). Core pipeline works offline.
- With 4 images, only one feature scene is available (fits up to 3 features).

## Future Scope

- AI-powered image recognition for automatic photo labelling
- More video templates and themes
- Watermark/logo overlay support
- Batch generation for property listing sheets
- Direct social media sharing integration

---

## License

This project was built as an assignment for the AI Developer role at **Realty Assistant Pvt. Ltd (Viraaj Ventures Group)**.

---

## Author

**Ramandeep Kaur**
B.E. CSE (AI & ML) | Chandigarh University | Batch of 2027
[GitHub](https://github.com/Raman19-code)
