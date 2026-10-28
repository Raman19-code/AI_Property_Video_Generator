"""Fact-grounded script and caption generator (deterministic templates).

How it works (simple version):
  1. We have a small set of fixed sentence templates (see TEMPLATES below).
  2. We drop ONLY the user's validated facts into the templates.
  3. A "grounding check" then re-reads the finished script and confirms that every
     number and every word comes from (a) the user's facts or (b) the template
     vocabulary. If something unknown sneaks in, the script is rejected.

Because nothing is "imagined" by a model, the script can never invent an amenity,
price, distance or claim. If a detail is missing it is simply left out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from src import config
from src.validators import PropertyDetails

# --------------------------------------------------------------------------- #
# Templates - the ONLY wording that is not supplied by the user.
# Keep them neutral: no adjectives such as "luxury", "spacious", "best" etc.
# --------------------------------------------------------------------------- #
TEMPLATES = {
    "hook_voice": "Introducing {name}, in {location}.",
    "intro_voice": "This {property_type} is priced at {price}.",
    "intro_subtitle": "Priced at {price}",
    "feature_label": "Key Features",
    "feature_voice": "Features include {features}.",
    "card_voice": "{label}: {value}.",
    "label_voice": "{label}.",
    "closing_voice": "{cta}. Contact {contact}.",
    "closing_voice_no_contact": "{cta}.",
    "joiner": "{a} and {b}",
    "card_labels": ("Location", "Property Type", "Price"),
}

_PLACEHOLDER = re.compile(r"\{[^}]*\}")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_NUMBER = re.compile(r"\d+")


@dataclass
class Scene:
    index: int
    kind: str                 # hook | intro | feature | card | closing
    image_index: int          # which uploaded image this scene uses
    label: str = ""           # small gold heading
    title: str = ""           # big white text
    subtitle: str = ""        # medium gold text
    lines: list[str] = field(default_factory=list)   # bullet lines
    voiceover: str = ""
    duration: float = 0.0     # seconds (set by generate_script)

    @property
    def caption(self) -> str:
        """All on-screen text of the scene as one readable string."""
        parts = [self.label, self.title, self.subtitle, *self.lines]
        return " | ".join(p for p in parts if p)


@dataclass
class VideoScript:
    scenes: list[Scene]
    scene_seconds: float
    omitted_features: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    image_labels: list[str] = field(default_factory=list)   # user's photo labels (also "supplied facts")

    @property
    def voiceover(self) -> str:
        return " ".join(s.voiceover for s in self.scenes if s.voiceover)

    @property
    def total_seconds(self) -> float:
        return len(self.scenes) * self.scene_seconds + config.FADE_SECONDS

    def to_text(self) -> str:
        out = ["VIDEO SCRIPT", "=" * 60, ""]
        for s in self.scenes:
            out.append(f"Scene {s.index + 1} ({s.kind}) - image #{s.image_index + 1} - {s.duration:.1f}s")
            out.append(f"  Caption  : {s.caption}")
            out.append(f"  Voice-over: {s.voiceover or '(none)'}")
            out.append("")
        out.append("FULL VOICE-OVER SCRIPT")
        out.append("-" * 60)
        out.append(self.voiceover)
        if self.omitted_features:
            out += ["", "NOT SHOWN (no room - upload more images to show them):", ", ".join(self.omitted_features)]
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _join_natural(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return TEMPLATES["joiner"].format(a=", ".join(items[:-1]), b=items[-1])


def _split_evenly(items: list[str], groups: int) -> list[list[str]]:
    """[a,b,c,d,e] into 3 groups -> [[a,b],[c,d],[e]]"""
    base, extra = divmod(len(items), groups)
    result, start = [], 0
    for i in range(groups):
        size = base + (1 if i < extra else 0)
        result.append(items[start:start + size])
        start += size
    return result


_STOP_WORDS = {"a", "an", "the", "of", "with", "and", "in", "for", "to", "at", "on", "from"}


def _stem(word: str) -> str:
    """Tiny stemmer: 'Bedrooms' and 'bedroom' become the same token."""
    word = word.lower()
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def _stems(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text) if len(w) > 2 and w.lower() not in _STOP_WORDS}


def match_score(feature: str, label: str) -> int:
    """How many (stemmed) words a feature and a photo label share. 0 = no match."""
    return len(_stems(feature) & _stems(label))


def _normalise_labels(labels: Sequence[str] | None, n_images: int) -> list[str]:
    cleaned = [re.sub(r"\s+", " ", str(x or "")).strip() for x in (labels or [])]
    cleaned = cleaned[:n_images]
    return cleaned + [""] * (n_images - len(cleaned))


def scene_seconds_for(n_images: int) -> float:
    """Pick a scene length so that the whole video lands between ~20 and ~33 seconds."""
    return min(config.MAX_SCENE_SECONDS, max(config.MIN_SCENE_SECONDS, config.TARGET_TOTAL_SECONDS / n_images))


# --------------------------------------------------------------------------- #
# Main generator
# --------------------------------------------------------------------------- #


def generate_script(details: PropertyDetails, n_images: int,
                    image_labels: Sequence[str] | None = None) -> VideoScript:
    """Create one scene per image: hook, intro, feature/fact scenes, closing enquiry.

    `image_labels` is optional: one short text per image (e.g. "Kitchen") that the user typed.
    It lets the generator put each feature next to the photo that shows it.
    """
    if not config.MIN_IMAGES <= n_images <= config.MAX_IMAGES:
        raise ValueError(f"Need {config.MIN_IMAGES}-{config.MAX_IMAGES} images, got {n_images}.")

    labels = _normalise_labels(image_labels, n_images)
    t = TEMPLATES
    d = details
    price = d.price_display
    scenes: list[Scene] = []
    warnings: list[str] = []

    def add(kind: str, **kw) -> None:
        scenes.append(Scene(index=len(scenes), kind=kind, image_index=len(scenes), **kw))

    # 1. Opening hook
    add("hook", title=d.name, subtitle=d.location,
        voiceover=t["hook_voice"].format(name=d.name, location=d.location))

    # 2. Property introduction
    add("intro", title=d.property_type, subtitle=t["intro_subtitle"].format(price=price),
        voiceover=t["intro_voice"].format(property_type=d.property_type, price=price))

    # 3. Middle scenes: features first, then plain fact cards if images are left over
    #    Step A: a feature goes next to the photo whose label matches it ("Kitchen" <-> "Modular kitchen").
    #    Step B: features that matched no photo fill the photos WITHOUT a label (so we never show
    #            "bedroom" text over a kitchen photo). Whatever is left over is reported, not hidden.
    middle = list(range(2, n_images - 1))          # image numbers used by the middle scenes
    slots: dict[int, list[str]] = {i: [] for i in middle}
    unmatched: list[str] = []
    for feat in d.features:
        best, best_score = None, 0
        for i in middle:
            if labels[i] and len(slots[i]) < config.MAX_FEATURES_PER_SCENE:
                score = match_score(feat, labels[i])
                if score > best_score:
                    best, best_score = i, score
        if best is None:
            unmatched.append(feat)
        else:
            slots[best].append(feat)

    free = [i for i in middle if not labels[i]]
    capacity = len(free) * config.MAX_FEATURES_PER_SCENE
    shown, omitted = unmatched[:capacity], unmatched[capacity:]
    if shown:
        for i, group in zip(free, _split_evenly(shown, min(len(free), len(shown)))):
            slots[i] = group
    if omitted:
        hint = ("A feature is shown with the photo whose label matches it (for example the label 'Kitchen' "
                "for 'Modular kitchen'); other features only go on photos that have no label. "
                if any(labels) else "")
        warnings.append(
            f"{len(omitted)} feature(s) did not fit in the video: {', '.join(omitted)}. "
            f"{hint}Upload more images (up to 8) or label fewer photos to show more features."
        )

    card_values = {"Location": d.location, "Property Type": d.property_type, "Price": price}
    cards_made = 0
    for i in middle:
        if slots[i]:
            add("feature", label=labels[i] or t["feature_label"], lines=slots[i],
                voiceover=t["feature_voice"].format(features=_join_natural(slots[i])))
        elif labels[i]:                                   # labelled photo with no feature: just name it
            add("card", label=d.name, title=labels[i], voiceover=t["label_voice"].format(label=labels[i]))
        else:                                             # unlabelled spare photo: show one plain fact
            label = t["card_labels"][cards_made % len(t["card_labels"])]
            cards_made += 1
            add("card", label=label, title=card_values[label],
                voiceover=t["card_voice"].format(label=label, value=card_values[label]))

    # 4. Closing enquiry prompt
    cta = d.cta or config.DEFAULT_CTA
    if d.contact:
        voice = t["closing_voice"].format(cta=cta, contact=d.contact)
    else:
        voice = t["closing_voice_no_contact"].format(cta=cta)
    add("closing", label=d.name, title=cta, subtitle=d.contact, voiceover=voice)

    seconds = scene_seconds_for(n_images)
    for s in scenes:
        s.duration = seconds

    return VideoScript(scenes=scenes, scene_seconds=seconds, omitted_features=omitted,
                       warnings=warnings, image_labels=labels)


# --------------------------------------------------------------------------- #
# Grounding check ("hallucination guard")
# --------------------------------------------------------------------------- #


def _template_vocabulary() -> set[str]:
    words: set[str] = set()
    for value in TEMPLATES.values():
        for text in (value if isinstance(value, tuple) else (value,)):
            words.update(w.lower() for w in _WORD.findall(_PLACEHOLDER.sub(" ", text)))
    words.update(w.lower() for w in _WORD.findall(config.DEFAULT_CTA))
    return words


def check_grounding(script: VideoScript, details: PropertyDetails) -> list[str]:
    """Return a list of problems. Empty list = every number and word is grounded."""
    facts = [details.name, details.location, details.price, details.currency,
             details.property_type, details.contact, details.cta, *details.features, *script.image_labels]
    fact_text = " ".join(facts)
    allowed_words = {w.lower() for w in _WORD.findall(fact_text)} | _template_vocabulary()
    allowed_numbers = set(_NUMBER.findall(fact_text))

    problems: list[str] = []
    for s in script.scenes:
        for text in (s.label, s.title, s.subtitle, *s.lines, s.voiceover):
            for num in _NUMBER.findall(text):
                if num not in allowed_numbers:
                    problems.append(f'Scene {s.index + 1}: number "{num}" is not in the supplied facts.')
            for word in _WORD.findall(text):
                if word.lower() not in allowed_words:
                    problems.append(f'Scene {s.index + 1}: word "{word}" is not in the supplied facts or templates.')
        for line in s.lines:
            if s.kind == "feature" and line not in details.features:
                problems.append(f'Scene {s.index + 1}: feature "{line}" was not supplied by the user.')
    return problems
