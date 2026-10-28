"""Headless tests of the Streamlit app (no browser needed) using Streamlit's AppTest."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _app():
    return AppTest.from_file(APP, default_timeout=240).run()


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_app_loads_without_errors():
    at = _app()
    assert not at.exception
    assert [t.value for t in at.text_input][:1] == [""]


def test_empty_form_shows_friendly_errors_not_a_crash():
    at = _app()
    at.session_state["image_source"] = "Use the bundled sample images"
    at = _button(at, "Generate video").click().run()
    assert not at.exception
    assert len(at.error) == 1 and "Property name is required" in at.error[0].value
    assert "Location is required" in at.error[0].value


def test_too_few_images_message_when_no_uploads():
    at = _app()
    at = _button(at, "Load sample property").click().run()
    at.session_state["image_source"] = "Upload my own photos"
    at = at.run()
    at = _button(at, "Generate video").click().run()
    assert not at.exception
    assert any("Please upload 4 to 8" in e.value for e in at.error)


@pytest.mark.slow
def test_sample_property_end_to_end_in_the_ui(tmp_path, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)     # keep the real outputs/ folder clean
    at = _app()
    at = _button(at, "Load sample property").click().run()
    assert at.session_state["f_name"] == "Maple Grove Residency"
    assert any("7 images selected" in s.value for s in at.success)
    assert at.session_state["label_2"] == "Bedroom"          # photo labels are pre-filled by the sample
    at = _button(at, "Generate video").click().run()
    assert not at.exception and not at.error
    res = at.session_state["result"]
    assert res["video"][4:8] == b"ftyp"                     # real MP4 container
    assert len(res["video"]) > 100_000
    assert len(res["scenes"]) == 7
    assert res["scenes"][2]["On-screen caption"] == "Bedroom | 3 bedrooms | Wardrobes in every bedroom"
    assert res["scenes"][-1]["On-screen caption"].startswith("Maple Grove Residency | Book a site visit today")
