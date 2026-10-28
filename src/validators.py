"""Validation for the property form and the uploaded images.

Rule of thumb: never crash on bad input. Every problem becomes a short,
human-readable message in `ValidationResult.errors` (blocking) or
`ValidationResult.warnings` (video can still be made).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Sequence

from PIL import Image, ImageOps, UnidentifiedImageError

from src import config

# --------------------------------------------------------------------------- #
# Data containers
# --------------------------------------------------------------------------- #


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class PropertyDetails:
    """Clean, validated facts. This is the ONLY source of truth for the script."""

    name: str
    location: str
    price: str
    currency: str
    property_type: str
    features: list[str]
    contact: str = ""
    cta: str = ""

    @property
    def price_display(self) -> str:
        return f"{config.CURRENCIES.get(self.currency, self.currency + ' ')}{self.price}"


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# split on newline / semicolon / comma - but NOT a comma between digits (1,200 sq ft)
_FEATURE_SPLIT = re.compile(r"[\n;]+|(?<!\d),|,(?!\d)")


def clean_text(value: str | None) -> str:
    """Remove control characters and squeeze whitespace."""
    if not value:
        return ""
    value = _CONTROL_CHARS.sub("", str(value))
    return re.sub(r"\s+", " ", value).strip()


def parse_features(raw: str | None) -> list[str]:
    """Turn 'Pool, Gym\\n3 bedrooms' into ['Pool', 'Gym', '3 bedrooms'] (duplicates removed)."""
    if not raw:
        return []
    seen: set[str] = set()
    features: list[str] = []
    for part in _FEATURE_SPLIT.split(str(raw)):
        item = clean_text(part).lstrip("-*• ").strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            features.append(item)
    return features


def _too_long(label: str, value: str, limit: int, errors: list[str]) -> None:
    if len(value) > limit:
        errors.append(f"{label} is too long ({len(value)} characters). Please keep it under {limit}.")


# --------------------------------------------------------------------------- #
# Form validation
# --------------------------------------------------------------------------- #


def validate_details(
    name: str,
    location: str,
    price: str,
    currency: str,
    property_type: str,
    features_raw: str,
    contact: str = "",
    cta: str = "",
) -> tuple[PropertyDetails | None, ValidationResult]:
    """Validate the form. Returns (details, result); details is None if there are errors."""
    result = ValidationResult()
    errors, warnings = result.errors, result.warnings

    name, location = clean_text(name), clean_text(location)
    price, property_type = clean_text(price), clean_text(property_type)
    contact, cta = clean_text(contact), clean_text(cta)
    currency = clean_text(currency).upper()
    features = parse_features(features_raw)

    # --- required fields ---
    if not name:
        errors.append("Property name is required.")
    if not location:
        errors.append("Location is required.")
    if not property_type:
        errors.append("Property type is required (for example: 3 BHK Apartment).")
    if not price:
        errors.append("Price is required.")
    elif not any(ch.isdigit() for ch in price):
        errors.append("Price must contain a number (for example: 85,00,000).")
    if currency not in config.CURRENCIES:
        errors.append(f"Currency must be one of: {', '.join(config.CURRENCIES)}.")
    if not features:
        errors.append("Please add at least one key feature (one per line or comma separated).")

    # --- length limits (long text would not fit on screen) ---
    _too_long("Property name", name, config.MAX_NAME, errors)
    _too_long("Location", location, config.MAX_LOCATION, errors)
    _too_long("Property type", property_type, config.MAX_TYPE, errors)
    _too_long("Price", price, config.MAX_PRICE, errors)
    _too_long("Contact details", contact, config.MAX_CONTACT, errors)
    _too_long("Call-to-action", cta, config.MAX_CTA, errors)
    if len(features) > config.MAX_FEATURES:
        errors.append(f"Too many features ({len(features)}). Please keep the best {config.MAX_FEATURES} or fewer.")
    for feat in features:
        if len(feat) > config.MAX_FEATURE:
            errors.append(f'Feature "{feat[:30]}..." is too long ({len(feat)} characters, max {config.MAX_FEATURE}).')

    # --- optional fields ---
    if contact:
        digits = sum(ch.isdigit() for ch in contact)
        if not (_EMAIL.search(contact) or digits >= 7):
            errors.append("Contact details should include a phone number (7+ digits) or an email address.")
    else:
        warnings.append("No contact details given - the last scene will show only the call-to-action.")
    if not cta:
        warnings.append(f'No call-to-action given - using the neutral default "{config.DEFAULT_CTA}".')

    if errors:
        return None, result
    return (
        PropertyDetails(
            name=name,
            location=location,
            price=price,
            currency=currency,
            property_type=property_type,
            features=features,
            contact=contact,
            cta=cta,
        ),
        result,
    )


# --------------------------------------------------------------------------- #
# Image validation
# --------------------------------------------------------------------------- #


def _load_one_image(filename: str, data: bytes) -> tuple[Image.Image | None, list[str], list[str]]:
    """Check one file. Returns (RGB image or None, errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    lower = filename.lower()

    if not lower.endswith(config.ALLOWED_EXTENSIONS):
        return None, [f'"{filename}": unsupported file type. Use JPG, JPEG or PNG.'], warnings
    if not data:
        return None, [f'"{filename}": the file is empty.'], warnings
    if len(data) > config.MAX_IMAGE_BYTES:
        mb = len(data) / (1024 * 1024)
        return None, [f'"{filename}": file is too large ({mb:.1f} MB, max {config.MAX_IMAGE_BYTES // (1024 * 1024)} MB).'], warnings

    try:
        probe = Image.open(BytesIO(data))
        fmt = probe.format
        width, height = probe.size
        probe.verify()  # cheap integrity check
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return None, [f'"{filename}": this file is not a valid image (it may be corrupted or renamed).'], warnings

    if fmt not in config.ALLOWED_FORMATS:
        return None, [f'"{filename}": the real format is {fmt}, not JPG/PNG. Please convert it first.'], warnings
    if min(width, height) < config.MIN_IMAGE_SIDE:
        return None, [f'"{filename}": too small ({width}x{height}). The shortest side must be at least {config.MIN_IMAGE_SIDE}px.'], warnings
    if width * height > config.MAX_IMAGE_PIXELS:
        return None, [f'"{filename}": resolution too high ({width}x{height}). Please resize it below {config.MAX_IMAGE_PIXELS // 1_000_000} megapixels.'], warnings

    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)  # fixes sideways phone photos
        img.load()  # a truncated file fails here, not later during rendering
        img = img.convert("RGB")
    except (OSError, SyntaxError, ValueError):
        return None, [f'"{filename}": the image data is damaged and could not be read.'], warnings

    if img.width < 1280 and img.height < 720:
        warnings.append(f'"{filename}": low resolution ({img.width}x{img.height}); it may look soft in the video.')
    return img, errors, warnings


def load_and_validate_images(
    files: Sequence[tuple[str, bytes]],
) -> tuple[list[Image.Image], ValidationResult]:
    """Validate uploaded files (name, bytes). Returns (RGB images in upload order, result).

    The returned list is empty whenever there are errors.
    """
    result = ValidationResult()
    count = len(files)

    if count == 0:
        result.errors.append(f"Please upload {config.MIN_IMAGES} to {config.MAX_IMAGES} property images.")
        return [], result
    if count < config.MIN_IMAGES:
        result.errors.append(f"You uploaded {count} image(s). Please upload at least {config.MIN_IMAGES}.")
    elif count > config.MAX_IMAGES:
        result.errors.append(f"You uploaded {count} images. The maximum is {config.MAX_IMAGES}; please remove {count - config.MAX_IMAGES}.")

    images: list[Image.Image] = []
    for filename, data in files:
        img, errs, warns = _load_one_image(filename, data)
        result.errors.extend(errs)
        result.warnings.extend(warns)
        if img is not None:
            images.append(img)

    if result.errors:
        return [], result
    return images, result


def validate_image_labels(labels: Sequence[str] | None) -> tuple[list[str], ValidationResult]:
    """Optional short label per photo (for example "Kitchen"). Empty labels are fine."""
    result = ValidationResult()
    cleaned = [clean_text(x) for x in (labels or [])]
    for i, label in enumerate(cleaned, start=1):
        if len(label) > config.MAX_IMAGE_LABEL:
            result.errors.append(
                f"Label of image {i} is too long ({len(label)} characters). Keep it under {config.MAX_IMAGE_LABEL}.")
    return cleaned, result
