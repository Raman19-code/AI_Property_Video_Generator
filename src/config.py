"""Central settings for the AI Property Video Generator.

Everything that you might want to tweak (limits, video size, timings) lives here,
so the other files stay clean.
"""
from pathlib import Path

# ---------- Folders ----------
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
SAMPLE_IMAGES_DIR = ASSETS_DIR / "sample_images"
FONT_DIR = ASSETS_DIR / "fonts"
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

# ---------- Image rules ----------
MIN_IMAGES = 4
MAX_IMAGES = 8
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")
ALLOWED_FORMATS = ("JPEG", "PNG")          # real format, checked by Pillow (not just the extension)
MAX_IMAGE_BYTES = 15 * 1024 * 1024         # 15 MB per image
MIN_IMAGE_SIDE = 400                       # pixels (shortest side)
MAX_IMAGE_PIXELS = 40_000_000              # protects 8GB RAM from giant images

# ---------- Text-field limits ----------
MAX_NAME = 80
MAX_LOCATION = 100
MAX_TYPE = 40
MAX_PRICE = 30
MAX_FEATURE = 50
MAX_FEATURES = 12
MAX_CONTACT = 100
MAX_CTA = 80
MAX_FEATURES_PER_SCENE = 3

CURRENCIES = {            # code -> symbol shown in the video
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "AED": "AED ",
}
DEFAULT_CTA = "Enquire today"   # neutral prompt used only when the user leaves the CTA empty

# ---------- Video settings ----------
FPS = 24
ASPECT_RATIOS = {
    "Landscape 16:9 (1280x720)": (1280, 720),
    "Vertical 9:16 (720x1280)": (720, 1280),
}
DEFAULT_ASPECT = "Landscape 16:9 (1280x720)"
TARGET_TOTAL_SECONDS = 30.0   # we aim for a 20-40 second video
MIN_SCENE_SECONDS = 4.0
MAX_SCENE_SECONDS = 5.0
FADE_SECONDS = 0.8            # crossfade length between scenes
ZOOM_AMOUNT = 0.06            # slow 6% zoom on every image ("Ken Burns" effect)

# ---------- Colours (R, G, B) ----------
COLOR_PANEL = (8, 14, 28)
COLOR_WHITE = (255, 255, 255)
COLOR_GOLD = (232, 190, 90)
COLOR_SOFT = (214, 220, 232)

KEEP_LAST_OUTPUTS = 15        # old generated videos are cleaned up automatically
