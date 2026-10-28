"""Script generator tests: structure, facts-only guarantee, length."""
import re

import pytest

from src import config
from src.script_generator import TEMPLATES, check_grounding, generate_script
from src.validators import validate_details


def make_details(**over):
    args = dict(name="Maple Grove", location="Sector 9", price="85,00,000", currency="INR",
                property_type="3 BHK Apartment", features_raw="3 bedrooms\n2 bathrooms\nBalcony\nParking\nSecurity",
                contact="+91 90000 00000", cta="Call us")
    args.update(over)
    d, res = validate_details(**args)
    assert d is not None, res.errors
    return d


@pytest.mark.parametrize("n", range(config.MIN_IMAGES, config.MAX_IMAGES + 1))
def test_one_scene_per_image_with_required_structure(n):
    d = make_details()
    script = generate_script(d, n)
    assert len(script.scenes) == n
    assert [s.image_index for s in script.scenes] == list(range(n))
    assert script.scenes[0].kind == "hook" and script.scenes[0].title == d.name
    assert script.scenes[1].kind == "intro"
    assert script.scenes[-1].kind == "closing"                       # final enquiry prompt
    assert script.scenes[-1].title == "Call us"
    assert script.scenes[-1].subtitle == d.contact
    assert check_grounding(script, d) == []


@pytest.mark.parametrize("n", range(config.MIN_IMAGES, config.MAX_IMAGES + 1))
def test_video_length_is_between_20_and_40_seconds(n):
    script = generate_script(make_details(), n)
    assert 20 <= script.total_seconds <= 40


@pytest.mark.parametrize("n", range(config.MIN_IMAGES, config.MAX_IMAGES + 1))
def test_voiceover_fits_the_video_length(n):
    script = generate_script(make_details(), n)
    words = len(script.voiceover.split())
    assert words / 2.5 <= script.total_seconds        # ~150 words per minute narration speed


def test_every_scene_has_caption_and_duration():
    script = generate_script(make_details(), 6)
    assert all(s.caption and s.duration > 0 for s in script.scenes)


def test_features_are_used_verbatim_and_only_from_user():
    d = make_details()
    script = generate_script(d, 8)
    shown = [line for s in script.scenes if s.kind == "feature" for line in s.lines]
    assert shown == d.features                      # all 5 shown, unchanged, in order


def test_too_many_features_are_reported_not_invented():
    d = make_details(features_raw="\n".join(f"Feature number {i}" for i in range(1, 9)))
    script = generate_script(d, 4)                  # 1 feature scene x 3 lines
    assert len([line for s in script.scenes for line in s.lines]) == 3
    assert len(script.omitted_features) == 5
    assert script.warnings and "did not fit" in script.warnings[0]
    assert check_grounding(script, d) == []


def test_few_features_many_images_uses_fact_cards_only():
    d = make_details(features_raw="Garden")
    script = generate_script(d, 8)
    kinds = [s.kind for s in script.scenes]
    assert kinds.count("feature") == 1 and kinds.count("card") == 4
    assert check_grounding(script, d) == []


def test_missing_contact_is_omitted_from_closing_scene():
    d = make_details(contact="")
    last = generate_script(d, 5).scenes[-1]
    assert last.subtitle == "" and "Contact" not in last.voiceover


def test_default_cta_used_when_empty():
    d = make_details(cta="")
    assert generate_script(d, 5).scenes[-1].title == config.DEFAULT_CTA


def test_price_in_script_matches_input_exactly():
    script = generate_script(make_details(), 5)
    assert script.scenes[1].subtitle == "Priced at ₹85,00,000"


def test_grounding_check_catches_invented_claims():
    d = make_details()
    script = generate_script(d, 5)
    script.scenes[2].lines.append("Swimming pool")                 # not supplied
    script.scenes[1].voiceover += " Only 5 km from the airport."   # invented distance
    problems = " ".join(check_grounding(script, d))
    assert "Swimming" in problems and '"5"' in problems and "airport" in problems


def test_templates_contain_no_marketing_superlatives():
    banned = {"luxury", "luxurious", "stunning", "best", "spacious", "premium", "dream", "perfect",
              "prime", "amazing", "beautiful", "exclusive", "world", "class", "unbeatable", "affordable"}
    words = set()
    for value in TEMPLATES.values():
        for text in (value if isinstance(value, tuple) else (value,)):
            words.update(re.findall(r"[a-z]+", text.lower()))
    assert words.isdisjoint(banned)


def test_no_api_keys_needed(monkeypatch):
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    assert generate_script(make_details(), 5).scenes


@pytest.mark.parametrize("n", [0, 3, 9])
def test_image_count_out_of_range_raises(n):
    with pytest.raises(ValueError):
        generate_script(make_details(), n)


def test_long_name_and_captions_stay_intact_in_script():
    d = make_details(name="A" * config.MAX_NAME, features_raw="B" * config.MAX_FEATURE)
    script = generate_script(d, 4)
    assert script.scenes[0].title == "A" * config.MAX_NAME
    assert check_grounding(script, d) == []
