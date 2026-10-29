"""Optional AI voice-over polish (off by default).

The rule-based script is always built first. If the user switches this on and supplies an
API key, an LLM may re-phrase each scene's *voice-over sentence* so it sounds more natural.

Safety design (why an LLM cannot invent a feature here):
* On-screen captions are never touched. They stay exactly the user's own words.
* Every rewrite is checked by `validate_rewrite()`: no new numbers, no words outside the
  user's facts / template words / a small list of neutral connecting words, every fact that
  the original sentence mentioned must still appear, and the length is capped.
* A rewrite that fails any check, a missing key, no internet or an API error all fall back to
  the original template sentence for that scene. Nothing crashes.
"""
from __future__ import annotations

import copy
import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable

from .script_generator import _NUMBER, _WORD, VideoScript, _template_vocabulary
from .validators import PropertyDetails

MAX_WORDS = 35
TIMEOUT_SECONDS = 25

# Neutral words an LLM may use to connect the user's facts. Deliberately has no adjectives
# that make claims (no "spacious", "luxury", "stunning", "perfect", "close", "near" ...).
NEUTRAL_WORDS = frozenset("""
a an the and or but in at on of to for with by from as is are be it its this that these those
your you our we us here there now today welcome discover meet introducing presenting home
homes features feature include includes including priced price contact call visit book enquire
enquiry inside offers offer comes come new find step explore enjoy located location
""".split())

PROVIDERS = {
    "Gemini (free key from Google AI Studio)": "gemini",
    "Anthropic (Claude)": "anthropic",
}
DEFAULT_MODELS = {"gemini": "gemini-1.5-flash", "anthropic": "claude-haiku-5-5"}

CompleteFn = Callable[[str], str]


# --------------------------------------------------------------------------- #
# Validation of a rewrite
# --------------------------------------------------------------------------- #
def _fact_strings(details: PropertyDetails, labels: list[str]) -> list[str]:
    return [details.name, details.location, details.price, details.property_type,
            details.contact, details.cta, *details.features, *labels]


def validate_rewrite(original: str, rewrite: str, details: PropertyDetails, labels: list[str]) -> list[str]:
    """Return a list of reasons the rewrite is rejected. Empty list = accepted."""
    problems: list[str] = []
    text = rewrite.strip()
    if not text:
        return ["empty answer"]
    if len(text.split()) > MAX_WORDS:
        problems.append(f"longer than {MAX_WORDS} words")
    facts = _fact_strings(details, labels)
    fact_text = " ".join(facts) + " " + details.currency
    allowed_numbers = set(_NUMBER.findall(fact_text))
    allowed_words = {w.lower() for w in _WORD.findall(fact_text)} | _template_vocabulary() | NEUTRAL_WORDS
    for num in _NUMBER.findall(text):
        if num not in allowed_numbers:
            problems.append(f'new number "{num}"')
    for word in _WORD.findall(text):
        if word.lower() not in allowed_words:
            problems.append(f'new word "{word}"')
    low = text.lower()
    for fact in facts:                              # facts used by the original must survive
        if fact and fact.lower() in original.lower() and fact.lower() not in low:
            problems.append(f'dropped fact "{fact}"')
    return problems


# --------------------------------------------------------------------------- #
# Provider calls (plain HTTPS, no extra library)
# --------------------------------------------------------------------------- #
def _post_json(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:   # noqa: S310 - fixed https URLs
        return json.loads(resp.read().decode("utf-8"))


def make_complete_fn(provider: str, api_key: str, model: str | None = None) -> CompleteFn:
    model = model or DEFAULT_MODELS[provider]
    if provider == "gemini":
        def call(prompt: str) -> str:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            data = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 120}},
                              {"x-goog-api-key": api_key})
            return data["candidates"][0]["content"]["parts"][0]["text"]
    elif provider == "anthropic":
        def call(prompt: str) -> str:
            data = _post_json("https://api.anthropic.com/v1/messages",
                              {"model": model, "max_tokens": 120, "temperature": 0.4,
                               "messages": [{"role": "user", "content": prompt}]},
                              {"x-api-key": api_key, "anthropic-version": "2023-06-01"})
            return data["content"][0]["text"]
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return call


def _prompt(original: str, details: PropertyDetails, labels: list[str]) -> str:
    facts = "\n".join(f"- {f}" for f in _fact_strings(details, labels) if f)
    return (
        "You polish one sentence of a real-estate video voice-over.\n"
        "Rules: use ONLY the facts below. Do not add any feature, number, distance, adjective "
        "that praises the property, or claim. Keep every fact that appears in the original. "
        f"Write at most {MAX_WORDS} words, plain English, one or two short sentences. "
        "Reply with the sentence only.\n\n"
        f"FACTS:\n{facts}\n\nORIGINAL SENTENCE:\n{original}\n"
    )


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def polish_voiceovers(script: VideoScript, details: PropertyDetails, complete: CompleteFn
                      ) -> tuple[VideoScript, list[str]]:
    """Return (new_script, notes). The input script is not modified."""
    new = copy.deepcopy(script)
    notes: list[str] = []
    accepted = 0
    for scene in new.scenes:
        original = scene.voiceover
        if not original:
            continue
        try:
            raw = complete(_prompt(original, details, script.image_labels))
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, OSError) as exc:
            notes.append(f"AI polish stopped at scene {scene.index + 1} ({type(exc).__name__}). "
                         "The rest of the script uses the standard sentences.")
            break
        rewrite = re.sub(r"\s+", " ", (raw or "")).strip().strip('"')
        problems = validate_rewrite(original, rewrite, details, script.image_labels)
        if problems:
            notes.append(f"Scene {scene.index + 1}: AI sentence rejected ({problems[0]}); kept the standard sentence.")
        else:
            scene.voiceover = rewrite
            accepted += 1
    notes.insert(0, f"AI polish: {accepted} of {len(new.scenes)} voice-over sentences accepted after safety checks.")
    return new, notes


def key_from_env(provider: str) -> str:
    name = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[provider]
    return os.environ.get(name, "")
