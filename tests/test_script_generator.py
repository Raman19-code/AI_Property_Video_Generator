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


# ---------------------------------------------------------------- photo labels (feature <-> photo matching)
from src.script_generator import match_score                      # noqa: E402
from src.validators import validate_image_labels                   # noqa: E402

LABELS_7 = ["Exterior", "Living room", "Bedroom", "Kitchen", "Bathroom", "Parking", "Balcony"]
FEATURES_5 = "3 bedrooms\nWardrobes in every bedroom\nModular kitchen\n2 bathrooms\nCovered parking"


def test_match_score_handles_plurals_case_and_unrelated_words():
    assert match_score("3 bedrooms", "BEDROOM") > 0
    assert match_score("Modular kitchen", "Kitchen") > 0
    assert match_score("Covered parking", "Living room") == 0
    assert match_score("2 bathrooms", "Bedroom") == 0


def test_each_feature_is_shown_with_its_matching_photo():
    d = make_details(features_raw=FEATURES_5)
    script = generate_script(d, 7, LABELS_7)
    by_label = {s.label: s for s in script.scenes if s.kind == "feature"}
    assert by_label["Bedroom"].lines == ["3 bedrooms", "Wardrobes in every bedroom"]
    assert by_label["Kitchen"].lines == ["Modular kitchen"]
    assert by_label["Bathroom"].lines == ["2 bathrooms"]
    assert by_label["Parking"].lines == ["Covered parking"]
    for s in script.scenes:                                          # the scene really uses that photo
        if s.kind == "feature":
            assert LABELS_7[s.image_index] == s.label
    assert check_grounding(script, d) == [] and script.warnings == []


def test_without_labels_behaviour_is_unchanged():
    d = make_details(features_raw=FEATURES_5)
    script = generate_script(d, 7)
    assert all(s.label == "Key Features" for s in script.scenes if s.kind == "feature")


def test_unmatched_feature_is_never_placed_on_a_wrongly_labelled_photo():
    d = make_details(features_raw="Modular kitchen\nSwimming pool")
    script = generate_script(d, 7, LABELS_7)
    shown = [line for s in script.scenes for line in s.lines]
    assert "Swimming pool" not in shown and script.omitted_features == ["Swimming pool"]
    assert "did not fit" in script.warnings[0] and "label" in script.warnings[0]


def test_unmatched_features_use_photos_without_a_label():
    d = make_details(features_raw="Modular kitchen\nGarden")
    script = generate_script(d, 6, ["", "", "", "Kitchen", "", ""])   # only the kitchen photo is labelled
    garden = next(s for s in script.scenes if "Garden" in s.lines)
    assert garden.image_index in (2, 4) and garden.label == "Key Features"
    assert script.omitted_features == []


def test_labelled_photo_without_matching_feature_becomes_a_label_card():
    d = make_details(features_raw="Modular kitchen")
    script = generate_script(d, 7, LABELS_7)
    cards = [s for s in script.scenes if s.kind == "card"]
    assert {c.title for c in cards} == {"Bedroom", "Bathroom", "Parking"}
    assert all(c.label == d.name for c in cards)
    assert check_grounding(script, d) == []


def test_at_most_three_features_per_photo():
    d = make_details(features_raw="\n".join(f"Bedroom {i}" for i in range(1, 6)))
    script = generate_script(d, 4, ["", "", "Bedroom", ""])
    assert len(script.scenes[2].lines) == 3 and len(script.omitted_features) == 2


def test_labels_count_as_supplied_facts_but_other_words_do_not():
    d = make_details(features_raw=FEATURES_5)
    script = generate_script(d, 7, LABELS_7)
    assert check_grounding(script, d) == []
    script.scenes[3].subtitle = "Luxury"
    assert any("Luxury" in p for p in check_grounding(script, d))


def test_short_label_list_and_blank_labels_are_padded():
    script = generate_script(make_details(), 5, ["Exterior"])
    assert script.image_labels == ["Exterior", "", "", "", ""]


def test_label_validation():
    cleaned, res = validate_image_labels(["  Kitchen ", "", "x" * 31])
    assert cleaned[0] == "Kitchen" and not res.ok and "image 3" in res.errors[0]
    assert validate_image_labels(None)[1].ok
