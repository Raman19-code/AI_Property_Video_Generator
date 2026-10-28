"""Builds the sample deliverables from the bundled synthetic data (no UI needed).

Run:  python scripts/generate_sample_video.py
Creates: outputs/sample_property_video.mp4 and outputs/sample_script.txt
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.script_generator import check_grounding, generate_script  # noqa: E402
from src.validators import load_and_validate_images, validate_details, validate_image_labels  # noqa: E402
from src.video_generator import generate_video  # noqa: E402


def main() -> None:
    data = json.loads((config.DATA_DIR / "sample_property.json").read_text(encoding="utf-8"))
    details, result = validate_details(
        data["name"], data["location"], data["price"], data["currency"], data["property_type"],
        "\n".join(data["features"]), data.get("contact", ""), data.get("cta", ""),
    )
    assert details, result.errors

    files = [(p.name, p.read_bytes()) for p in sorted(config.SAMPLE_IMAGES_DIR.glob("*.jpg"))]
    images, img_result = load_and_validate_images(files)
    assert images, img_result.errors

    labels, label_result = validate_image_labels(data.get("image_labels", []))
    assert label_result.ok, label_result.errors
    script = generate_script(details, len(images), labels)
    problems = check_grounding(script, details)
    assert not problems, problems

    out_video = config.OUTPUT_DIR / "sample_property_video.mp4"
    start = time.time()
    generate_video(images, script, out_video,
                   progress=lambda f, m: print(f"\r{f * 100:5.1f}%  {m:<55}", end="", flush=True))
    print(f"\nVideo saved: {out_video}  ({time.time() - start:.1f}s)")

    out_script = config.OUTPUT_DIR / "sample_script.txt"
    out_script.write_text(script.to_text(), encoding="utf-8")
    print(f"Script saved: {out_script}")


if __name__ == "__main__":
    main()
