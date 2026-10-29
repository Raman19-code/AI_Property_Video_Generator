"""AI Property Video Generator - Streamlit user interface.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

from src import config, llm_rewriter
from src.script_generator import check_grounding, generate_script
from src.validators import load_and_validate_images, validate_details, validate_image_labels
from src.video_generator import (VideoGenerationError, generate_video, prune_old_outputs,
                                 slugify)

st.set_page_config(page_title="AI Property Video Generator", page_icon="\U0001F3E0", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      .hero {background: linear-gradient(120deg,#0e1b33 0%,#1f3a5f 100%); color:#fff;
             padding: 1.6rem 2rem; border-radius: 14px; margin-bottom: 1.2rem;}
      .hero h1 {margin:0; font-size:2rem; color:#fff;}
      .hero p {margin:.4rem 0 0 0; color:#d9e2f1; font-size:1.02rem;}
      .hero .gold {color:#e8be5a; font-weight:600;}
      div.stButton > button[kind="primary"] {background:#1f3a5f; border:0; font-weight:600;}
    </style>
    <div class="hero">
      <h1>\U0001F3E0 AI Property Video Generator</h1>
      <p>Enter the property facts, add <span class="gold">4&ndash;8 photos</span>, and get a ready-to-share
      promotional MP4 in a minute. The script uses <b>only the facts you type</b> &ndash; nothing is invented.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Form defaults + sample data
# --------------------------------------------------------------------------- #
FIELDS = {"f_name": "", "f_location": "", "f_price": "", "f_currency": "INR", "f_type": "",
          "f_features": "", "f_contact": "", "f_cta": ""}
for key, default in FIELDS.items():
    st.session_state.setdefault(key, default)


def load_sample() -> None:
    data = json.loads((config.DATA_DIR / "sample_property.json").read_text(encoding="utf-8"))
    st.session_state.update(
        f_name=data["name"], f_location=data["location"], f_price=data["price"],
        f_currency=data["currency"], f_type=data["property_type"],
        f_features="\n".join(data["features"]), f_contact=data.get("contact", ""),
        f_cta=data.get("cta", ""), image_source="Use the bundled sample images",
    )
    sample_labels = data.get("image_labels", [])
    for i in range(config.MAX_IMAGES + 4):
        st.session_state[f"label_{i}"] = sample_labels[i] if i < len(sample_labels) else ""


def clear_form() -> None:
    st.session_state.update(FIELDS)
    for i in range(config.MAX_IMAGES + 4):
        st.session_state[f"label_{i}"] = ""
    st.session_state.pop("result", None)
    st.session_state["image_source"] = "Upload my own photos"


form_col, media_col = st.columns([1, 1], gap="large")

# --------------------------------------------------------------------------- #
# Inputs: details (left) and images + generate button (right)
# --------------------------------------------------------------------------- #
with form_col:
    st.subheader("1. Property details")
    b1, b2 = st.columns(2)
    b1.button("Load sample property", on_click=load_sample, use_container_width=True,
              help="Fills the form with fictional demo data and selects the sample images.")
    b2.button("Clear form", on_click=clear_form, use_container_width=True)

    st.text_input("Property name *", key="f_name", placeholder="e.g. Maple Grove Residency", max_chars=200)
    st.text_input("Location *", key="f_location", placeholder="e.g. Sector 99, Demo City", max_chars=300)
    c1, c2 = st.columns([1, 2])
    c1.selectbox("Currency *", list(config.CURRENCIES), key="f_currency")
    c2.text_input("Price *", key="f_price", placeholder="e.g. 85,00,000", max_chars=60)
    st.text_input("Property type *", key="f_type", placeholder="e.g. 3 BHK Apartment", max_chars=200)
    st.text_area("Key features * (one per line, or comma separated)", key="f_features", height=130,
                 placeholder="3 bedrooms\n2 bathrooms\nCovered parking")
    st.text_input("Contact details", key="f_contact", placeholder="Phone and/or email", max_chars=300)
    st.text_input("Call-to-action message", key="f_cta", placeholder="e.g. Book a site visit today", max_chars=300)

with media_col:
    st.subheader("2. Property images")
    source = st.radio("Image source", ["Upload my own photos", "Use the bundled sample images"],
                      key="image_source", horizontal=True)
    files: list[tuple[str, bytes]] = []
    if source == "Upload my own photos":
        uploads = st.file_uploader(f"Upload {config.MIN_IMAGES}-{config.MAX_IMAGES} images (JPG or PNG)",
                                   type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        files = [(u.name, u.getvalue()) for u in uploads or []]
    else:
        files = [(p.name, p.read_bytes()) for p in sorted(config.SAMPLE_IMAGES_DIR.glob("*.jpg"))]
        st.caption("Synthetic illustrations (not real photos) are used for the demo.")

    # live feedback on the image count
    n = len(files)
    if n == 0:
        st.info(f"No images yet. Please add {config.MIN_IMAGES} to {config.MAX_IMAGES}.")
    elif config.MIN_IMAGES <= n <= config.MAX_IMAGES:
        st.success(f"{n} images selected - good to go.")
    else:
        st.warning(f"{n} images selected. You need between {config.MIN_IMAGES} and {config.MAX_IMAGES}.")
    if files:
        st.caption("Optional: write what each photo shows (for example Kitchen). The video then shows each "
                   "feature with the matching photo. Photos are used in this order: the first is the opening "
                   "shot and the last one carries the enquiry message.")
        cols = st.columns(4)
        for i, (name, data) in enumerate(files[:config.MAX_IMAGES + 4]):
            try:
                cols[i % 4].image(data, caption=f"{i + 1}. {name}", use_container_width=True)
            except Exception:  # a broken file is reported properly when you press Generate
                cols[i % 4].caption(f"{i + 1}. {name} (cannot preview)")
            cols[i % 4].text_input(f"Label for photo {i + 1}", key=f"label_{i}", placeholder="e.g. Kitchen",
                                   label_visibility="collapsed", max_chars=60)

    st.subheader("3. Video format")
    aspect_name = st.selectbox("Aspect ratio", list(config.ASPECT_RATIOS),
                               index=list(config.ASPECT_RATIOS).index(config.DEFAULT_ASPECT))
    use_narration = st.checkbox("Add spoken narration (optional, needs internet)", value=False,
                               help="Converts the voice-over script to speech using Google Text-to-Speech (free, no key).")
    use_music = st.checkbox("Add soft background music (optional)", value=False,
                            help="A calm original tune generated by the app. Music volume is lowered when narration is on.")
    own_audio = st.file_uploader("Or use your own background audio (optional, MP3/WAV/M4A, max 15 MB)",
                                 type=[e.lstrip(".") for e in config.AUDIO_EXTENSIONS])
    with st.expander("Advanced: AI voice-over polish (optional)"):
        st.caption("Rewrites only the voice-over sentences so they sound more natural. On-screen captions stay exactly "
                   "as you typed them. Every AI sentence is checked against your facts; if it adds anything new it is "
                   "thrown away. Needs internet and your own API key (not saved).")
        use_ai = st.checkbox("Use AI to polish the voice-over", value=False)
        provider_label = st.selectbox("Provider", list(llm_rewriter.PROVIDERS))
        api_key = st.text_input("API key", type="password",
                                value=llm_rewriter.key_from_env(llm_rewriter.PROVIDERS[provider_label]))
    generate = st.button("Generate video", type="primary", use_container_width=True)

# --------------------------------------------------------------------------- #
# Generate
# --------------------------------------------------------------------------- #
if generate:
    st.session_state.pop("result", None)
    with media_col:
        details, d_res = validate_details(
            st.session_state.f_name, st.session_state.f_location, st.session_state.f_price,
            st.session_state.f_currency, st.session_state.f_type, st.session_state.f_features,
            st.session_state.f_contact, st.session_state.f_cta,
        )
        images, i_res = load_and_validate_images(files)
        labels, l_res = validate_image_labels(
            [st.session_state.get(f"label_{i}", "") for i in range(len(files))])
        errors = d_res.errors + i_res.errors + l_res.errors
        warnings = d_res.warnings + i_res.warnings

        if errors:
            st.error("Please fix the following before generating:\n\n" + "\n".join(f"- {e}" for e in errors))
            for w in warnings:
                st.warning(w)
        else:
            script = generate_script(details, len(images), labels)
            problems = check_grounding(script, details)
            if problems:   # should never happen with the built-in templates; guard anyway
                st.error("Safety check failed: the script contained unsupported text.\n\n"
                         + "\n".join(f"- {p}" for p in problems))
            else:
                warnings += script.warnings
                if use_ai:
                    if not api_key.strip():
                        warnings.append("AI polish is on but no API key was entered, so the standard script is used.")
                    else:
                        with st.spinner("Asking the AI to polish the voice-over..."):
                            complete = llm_rewriter.make_complete_fn(llm_rewriter.PROVIDERS[provider_label], api_key.strip())
                            script, ai_notes = llm_rewriter.polish_voiceovers(script, details, complete)
                        warnings += ai_notes
                bar = st.progress(0.0, text="Starting...")
                started = time.time()
                audio_path = None
                if own_audio is not None:
                    if own_audio.size > config.MAX_AUDIO_BYTES:
                        warnings.append("Your audio file is larger than 15 MB, so it was not used.")
                    else:
                        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                        suffix = Path(own_audio.name).suffix.lower()
                        audio_path = config.OUTPUT_DIR / f"_upload_audio{suffix}"
                        audio_path.write_bytes(own_audio.getvalue())
                try:
                    out_path = config.OUTPUT_DIR / f"{slugify(details.name)}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
                    generate_video(images, script, out_path, aspect=config.ASPECT_RATIOS[aspect_name],
                                   progress=lambda frac, msg: bar.progress(min(frac, 1.0), text=msg),
                                   music=use_music, audio_file=audio_path, narration=use_narration)
                    script_path = out_path.with_name(out_path.stem + "_script.txt")
                    script_path.write_text(script.to_text(), encoding="utf-8")
                    prune_old_outputs()
                    st.session_state["result"] = {
                        "video": out_path.read_bytes(), "name": out_path.name,
                        "script_text": script.to_text(), "voiceover": script.voiceover,
                        "scenes": [{"Scene": s.index + 1, "Type": s.kind, "Image": s.image_index + 1,
                                    "On-screen caption": s.caption, "Voice-over": s.voiceover,
                                    "Seconds": s.duration} for s in script.scenes],
                        "warnings": warnings, "seconds": time.time() - started,
                        "length": script.total_seconds,
                    }
                    bar.empty()
                except VideoGenerationError as exc:
                    bar.empty()
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - last safety net, the app must not crash
                    bar.empty()
                    st.error(f"Something unexpected went wrong: {exc}")
                finally:
                    if audio_path is not None:
                        audio_path.unlink(missing_ok=True)   # do not keep the uploaded audio

# --------------------------------------------------------------------------- #
# Result (full width, right below the inputs). Kept in session_state so it
# survives button clicks such as "Download", which re-run the script.
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Result")
res = st.session_state.get("result")
if not res:
    st.info("Your video, script and captions will appear here after you press **Generate video**.")
else:
    st.success(f"Video ready - about {res['length']:.0f} seconds long, made in {res['seconds']:.0f} seconds.")
    for w in res["warnings"]:
        st.warning(w)
    video_col, text_col = st.columns([3, 2], gap="large")
    with video_col:
        st.video(res["video"], format="video/mp4")
        d1, d2 = st.columns(2)
        d1.download_button("Download MP4", res["video"], file_name=res["name"], mime="video/mp4",
                           use_container_width=True, type="primary")
        d2.download_button("Download script (.txt)", res["script_text"],
                           file_name=res["name"].replace(".mp4", "_script.txt"), mime="text/plain",
                           use_container_width=True)
    with text_col:
        tab1, tab2 = st.tabs(["Scene captions", "Voice-over script"])
        with tab1:
            st.dataframe(res["scenes"], use_container_width=True, hide_index=True)
        with tab2:
            st.write(res["voiceover"])
            st.caption("Tick 'Add spoken narration' above to hear the voice-over. Optional background music can also be added.")
