"""Form + image validation tests (fast, no video rendering)."""
import io

import pytest
from PIL import Image

from src import config
from src.validators import load_and_validate_images, parse_features, validate_details
from tests.conftest import good_files, make_image_bytes


def valid_args(**over):
    args = dict(name="Maple Grove", location="Sector 9", price="85,00,000", currency="INR",
                property_type="3 BHK Apartment", features_raw="3 bedrooms\nBalcony",
                contact="+91 90000 00000", cta="Call us")
    args.update(over)
    return args


# ---------------- form: happy path ----------------
def test_valid_details_accepted():
    d, res = validate_details(**valid_args())
    assert res.ok and d is not None
    assert d.price_display == "₹85,00,000"
    assert d.features == ["3 bedrooms", "Balcony"]


def test_features_split_but_numbers_with_commas_survive():
    assert parse_features("1,200 sq ft, Pool; Gym\n- Garden") == ["1,200 sq ft", "Pool", "Gym", "Garden"]
    assert parse_features("Pool, pool, POOL") == ["Pool"]          # duplicates removed
    assert parse_features("") == [] and parse_features(None) == []


def test_extra_whitespace_and_control_chars_cleaned():
    d, res = validate_details(**valid_args(name="  Maple \x00 Grove \n "))
    assert d.name == "Maple Grove"


# ---------------- form: missing / invalid ----------------
@pytest.mark.parametrize("field,expected", [
    ("name", "name is required"), ("location", "Location is required"),
    ("price", "Price is required"), ("property_type", "Property type is required"),
    ("features_raw", "at least one key feature"),
])
def test_missing_required_field(field, expected):
    d, res = validate_details(**valid_args(**{field: "   "}))
    assert d is None and not res.ok
    assert any(expected.lower() in e.lower() for e in res.errors)


def test_all_empty_gives_many_errors_not_a_crash():
    d, res = validate_details("", "", "", "INR", "", "", "", "")
    assert d is None and len(res.errors) >= 5


def test_price_must_contain_a_number():
    d, res = validate_details(**valid_args(price="cheap"))
    assert d is None and any("number" in e for e in res.errors)


def test_unknown_currency_rejected():
    d, res = validate_details(**valid_args(currency="XYZ"))
    assert d is None and any("Currency" in e for e in res.errors)


def test_missing_contact_is_warning_not_error():
    d, res = validate_details(**valid_args(contact=""))
    assert d is not None and res.ok
    assert any("contact" in w.lower() for w in res.warnings)


def test_missing_cta_is_warning_not_error():
    d, res = validate_details(**valid_args(cta=""))
    assert d is not None and any("call-to-action" in w.lower() for w in res.warnings)


@pytest.mark.parametrize("contact", ["hello", "12345", "call me maybe"])
def test_invalid_contact_rejected(contact):
    d, res = validate_details(**valid_args(contact=contact))
    assert d is None and any("Contact" in e for e in res.errors)


@pytest.mark.parametrize("contact", ["agent@example.com", "+91 98765 43210", "Priya: 98765 43210 / p@x.in"])
def test_valid_contact_accepted(contact):
    d, res = validate_details(**valid_args(contact=contact))
    assert d is not None


def test_long_name_and_features_rejected():
    d, res = validate_details(**valid_args(name="N" * (config.MAX_NAME + 1)))
    assert d is None and any("too long" in e for e in res.errors)
    d, res = validate_details(**valid_args(features_raw="x" * (config.MAX_FEATURE + 1)))
    assert d is None and any("too long" in e for e in res.errors)
    d, res = validate_details(**valid_args(features_raw="\n".join(f"f{i}" for i in range(config.MAX_FEATURES + 1))))
    assert d is None and any("Too many" in e for e in res.errors)


def test_maximum_allowed_name_is_accepted():
    d, res = validate_details(**valid_args(name="N" * config.MAX_NAME))
    assert d is not None


# ---------------- images ----------------
@pytest.mark.parametrize("n", [4, 5, 8])
def test_valid_image_counts_accepted(n):
    imgs, res = load_and_validate_images(good_files(n))
    assert res.ok and len(imgs) == n
    assert all(i.mode == "RGB" for i in imgs)


@pytest.mark.parametrize("n,fragment", [(0, "upload"), (3, "at least 4"), (9, "maximum is 8")])
def test_wrong_image_count_rejected(n, fragment):
    imgs, res = load_and_validate_images(good_files(n))
    assert imgs == [] and any(fragment in e for e in res.errors)


@pytest.mark.parametrize("name", ["a.gif", "b.bmp", "c.txt", "d.pdf", "noextension"])
def test_unsupported_extension_rejected(name):
    files = good_files(4) + [(name, make_image_bytes())]
    imgs, res = load_and_validate_images(files)
    assert imgs == [] and any("unsupported file type" in e for e in res.errors)


def test_corrupted_image_rejected():
    files = good_files(3) + [("broken.jpg", b"this is definitely not an image" * 50)]
    imgs, res = load_and_validate_images(files)
    assert imgs == [] and any("broken.jpg" in e and "not a valid image" in e for e in res.errors)


def test_truncated_image_rejected():
    data = make_image_bytes(seed=3)
    files = good_files(3) + [("cut.jpg", data[: len(data) // 2])]
    imgs, res = load_and_validate_images(files)
    assert imgs == [] and any("cut.jpg" in e for e in res.errors)


def test_gif_renamed_to_jpg_rejected():
    files = good_files(3) + [("fake.jpg", make_image_bytes(fmt="GIF"))]
    imgs, res = load_and_validate_images(files)
    assert imgs == [] and any("real format is GIF" in e for e in res.errors)


def test_empty_file_and_tiny_image_rejected():
    files = good_files(2) + [("empty.png", b"")] + [("tiny.png", make_image_bytes((100, 100), "PNG"))]
    imgs, res = load_and_validate_images(files)
    assert imgs == []
    assert any("empty" in e for e in res.errors) and any("too small" in e for e in res.errors)


def test_oversized_file_rejected():
    big = b"\xff\xd8" + b"\0" * (config.MAX_IMAGE_BYTES + 10)
    imgs, res = load_and_validate_images(good_files(3) + [("huge.jpg", big)])
    assert imgs == [] and any("too large" in e for e in res.errors)


def test_png_with_transparency_converted_to_rgb():
    files = good_files(3) + [("logo.png", make_image_bytes(fmt="PNG", mode="RGBA"))]
    imgs, res = load_and_validate_images(files)
    assert res.ok and imgs[3].mode == "RGB"


def test_exif_rotation_is_applied():
    img = Image.new("RGB", (1200, 800), (200, 10, 10))
    exif = Image.Exif()
    exif[0x0112] = 6                       # "rotate 90 degrees"
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    imgs, res = load_and_validate_images(good_files(3) + [("phone.jpg", buf.getvalue())])
    assert res.ok and imgs[3].size == (800, 1200)


def test_low_resolution_gives_warning_not_error():
    files = good_files(3) + [("small.jpg", make_image_bytes((900, 600)))]
    imgs, res = load_and_validate_images(files)
    assert res.ok and any("low resolution" in w for w in res.warnings)
