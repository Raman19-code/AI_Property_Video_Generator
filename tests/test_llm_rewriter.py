"""AI voice-over polish: the LLM is replaced by fake functions, so no network or key is needed."""
import urllib.error

from src.llm_rewriter import polish_voiceovers, validate_rewrite
from src.script_generator import check_grounding, generate_script
from src.validators import validate_details


def _details():
    d, res = validate_details("Maple Grove", "Sector 9", "85,00,000", "INR", "3 BHK Apartment",
                              "3 bedrooms\nModular kitchen\nCovered parking", "+91 90000 00000", "Call us today")
    assert d is not None, res.errors
    return d


def _script(d):
    return generate_script(d, 6, ["Exterior", "Living room", "Bedroom", "Kitchen", "Parking", ""])


def test_good_rewrite_is_accepted():
    d = _details()
    original = "Introducing Maple Grove, in Sector 9."
    assert validate_rewrite(original, "Welcome to Maple Grove, in Sector 9.", d, []) == []


def test_invented_things_are_rejected():
    d = _details()
    original = "Introducing Maple Grove, in Sector 9."
    for bad in ["Welcome to Maple Grove, in Sector 9, with a swimming pool.",       # new feature words
                "Welcome to Maple Grove, in Sector 9, only 5 minutes from the metro.",  # new number + words
                "A stunning home in Sector 9.",                                       # dropped name + claim word
                "Welcome to Maple Grove, in Sector 9. " + "Home " * 40]:              # too long
        assert validate_rewrite(original, bad, d, []), bad


def test_price_must_survive():
    d = _details()
    original = "This 3 BHK Apartment is priced at 85,00,000."
    assert validate_rewrite(original, "Meet this 3 BHK Apartment.", d, [])


def test_polish_keeps_only_safe_sentences_and_never_touches_captions():
    d = _details()
    script = _script(d)
    before_captions = [s.caption for s in script.scenes]

    def fake(prompt):
        if "Introducing" in prompt.split("ORIGINAL SENTENCE:")[1]:
            return "Welcome to Maple Grove, in Sector 9."          # safe
        return "A luxurious home with a private pool."              # unsafe
    new, notes = polish_voiceovers(script, d, fake)
    assert new.scenes[0].voiceover == "Welcome to Maple Grove, in Sector 9."
    assert all(n.voiceover == o.voiceover for n, o in zip(new.scenes[1:], script.scenes[1:]))
    assert [s.caption for s in new.scenes] == before_captions
    assert "1 of" in notes[0] and any("rejected" in n for n in notes)
    assert check_grounding(script, d) == []        # original script is unchanged


def test_api_failure_falls_back_to_template():
    d = _details()
    script = _script(d)

    def broken(prompt):
        raise urllib.error.URLError("no internet")
    new, notes = polish_voiceovers(script, d, broken)
    assert [s.voiceover for s in new.scenes] == [s.voiceover for s in script.scenes]
    assert any("stopped" in n for n in notes)


def test_garbage_answers_do_not_crash():
    d = _details()
    new, notes = polish_voiceovers(_script(d), d, lambda p: "")
    assert notes[0].startswith("AI polish: 0 of")
