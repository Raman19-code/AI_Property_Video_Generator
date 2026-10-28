"""Creates 6 synthetic, copyright-free illustration images for the demo.

Run:  python scripts/make_sample_images.py
They are drawn with Pillow (flat-style illustrations), contain no text, and are NOT
real photos of any property.
"""
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1600, 900
OUT = Path(__file__).resolve().parent.parent / "assets" / "sample_images"


def gradient(draw, top, bottom, y0=0, y1=H):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=c)


def exterior():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    gradient(d, (120, 180, 235), (225, 238, 250), 0, 600)
    d.ellipse([1240, 70, 1360, 190], fill=(255, 236, 170))
    d.rectangle([0, 600, W, H], fill=(96, 150, 92))
    d.rectangle([0, 760, W, H], fill=(84, 84, 92))
    d.rectangle([420, 190, 1180, 640], fill=(236, 226, 210))
    d.polygon([(390, 190), (800, 80), (1210, 190)], fill=(150, 78, 62))
    for row in range(3):
        for col in range(4):
            x, y = 470 + col * 175, 235 + row * 130
            d.rectangle([x, y, x + 105, y + 82], fill=(150, 200, 230), outline=(255, 255, 255), width=6)
    d.rectangle([740, 520, 860, 640], fill=(110, 72, 52))
    for cx in (260, 1340):
        d.rectangle([cx - 14, 480, cx + 14, 640], fill=(100, 70, 45))
        d.ellipse([cx - 110, 330, cx + 110, 550], fill=(52, 120, 70))
    return im


def living_room():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 640], fill=(238, 230, 218))
    d.rectangle([0, 640, W, H], fill=(172, 128, 92))
    d.rectangle([980, 120, 1480, 500], fill=(255, 255, 255))
    d.rectangle([996, 136, 1464, 484], fill=(170, 214, 240))
    d.line([(1230, 136), (1230, 484)], fill=(255, 255, 255), width=10)
    d.rounded_rectangle([160, 400, 940, 640], 40, fill=(70, 98, 130))
    d.rounded_rectangle([130, 460, 230, 660], 30, fill=(58, 84, 114))
    d.rounded_rectangle([870, 460, 970, 660], 30, fill=(58, 84, 114))
    d.rounded_rectangle([210, 380, 520, 520], 30, fill=(90, 120, 156))
    d.ellipse([260, 740, 1000, 880], fill=(214, 196, 170))
    d.rounded_rectangle([420, 690, 760, 760], 14, fill=(120, 84, 58))
    d.rectangle([1100, 520, 1112, 700], fill=(60, 60, 60))
    d.polygon([(1060, 520), (1150, 520), (1130, 450), (1080, 450)], fill=(250, 220, 140))
    return im


def kitchen():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], fill=(232, 236, 238))
    for x in range(0, W, 80):
        d.line([(x, 0), (x, 560)], fill=(214, 220, 224), width=2)
    for y in range(0, 560, 80):
        d.line([(0, y), (W, y)], fill=(214, 220, 224), width=2)
    d.rectangle([0, 0, W, 190], fill=(196, 200, 206))
    for x in range(40, W - 100, 300):
        d.rectangle([x, 30, x + 270, 170], fill=(244, 244, 246), outline=(160, 164, 170), width=4)
        d.ellipse([x + 120, 90, x + 150, 120], fill=(150, 154, 160))
    d.rectangle([0, 600, W, 640], fill=(70, 74, 82))
    d.rectangle([0, 640, W, H], fill=(206, 210, 214))
    for x in range(0, W, 320):
        d.rectangle([x + 10, 660, x + 300, 880], fill=(240, 240, 242), outline=(160, 164, 170), width=4)
        d.ellipse([x + 140, 750, x + 170, 780], fill=(150, 154, 160))
    d.rectangle([560, 575, 940, 600], fill=(40, 40, 44))
    for cx in (620, 700, 780, 860):
        d.ellipse([cx - 22, 580, cx + 22, 596], fill=(200, 60, 50))
    d.rectangle([1160, 330, 1420, 600], fill=(190, 196, 202), outline=(150, 156, 162), width=5)
    return im


def bedroom():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 660], fill=(226, 232, 244))
    d.rectangle([0, 660, W, H], fill=(190, 150, 112))
    d.rectangle([1120, 110, 1500, 460], fill=(255, 255, 255))
    d.rectangle([1136, 126, 1484, 444], fill=(176, 220, 244))
    d.rectangle([300, 230, 1000, 400], fill=(120, 86, 62))
    d.rounded_rectangle([260, 380, 1040, 700], 24, fill=(244, 244, 248))
    d.rounded_rectangle([260, 520, 1040, 700], 24, fill=(120, 150, 196))
    d.rounded_rectangle([320, 410, 560, 500], 30, fill=(255, 255, 255), outline=(210, 214, 224), width=4)
    d.rounded_rectangle([740, 410, 980, 500], 30, fill=(255, 255, 255), outline=(210, 214, 224), width=4)
    d.rectangle([1080, 560, 1240, 700], fill=(150, 108, 76))
    d.ellipse([1130, 500, 1190, 560], fill=(250, 214, 130))
    return im


def balcony():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    gradient(d, (250, 190, 130), (150, 190, 230), 0, 560)
    d.ellipse([1100, 330, 1260, 490], fill=(255, 226, 150))
    for i, x in enumerate(range(0, W, 140)):
        h = 160 + (i * 53) % 190
        d.rectangle([x, 560 - h, x + 120, 560], fill=(86 + i * 4 % 30, 104, 140))
    d.rectangle([0, 560, W, H], fill=(196, 168, 140))
    d.rectangle([0, 560, W, 580], fill=(60, 66, 76))
    for x in range(30, W, 70):
        d.rectangle([x, 580, x + 14, 760], fill=(60, 66, 76))
    d.rectangle([0, 760, W, 790], fill=(60, 66, 76))
    for cx in (260, 1200):
        d.polygon([(cx - 80, 700), (cx + 80, 700), (cx + 60, 860), (cx - 60, 860)], fill=(176, 100, 70))
        d.ellipse([cx - 110, 560, cx + 110, 720], fill=(60, 140, 76))
    d.rounded_rectangle([600, 700, 900, 780], 20, fill=(110, 80, 60))
    d.rectangle([640, 780, 660, 860], fill=(110, 80, 60)); d.rectangle([840, 780, 860, 860], fill=(110, 80, 60))
    return im


def parking():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 520], fill=(214, 218, 224))
    d.rectangle([0, 520, W, H], fill=(112, 116, 124))
    d.rectangle([0, 0, W, 130], fill=(160, 166, 176))
    for x in (60, 780, 1500):
        d.rectangle([x, 130, x + 40, 560], fill=(176, 180, 188))
    for x in range(120, W, 330):
        d.polygon([(x, 880), (x + 18, 880), (x + 98, 560), (x + 80, 560)], fill=(240, 240, 240))
    d.rounded_rectangle([250, 560, 720, 740], 40, fill=(190, 50, 50))
    d.polygon([(330, 560), (410, 480), (600, 480), (660, 560)], fill=(170, 40, 44))
    d.polygon([(370, 556), (425, 498), (500, 498), (500, 556)], fill=(170, 210, 236))
    d.polygon([(515, 556), (515, 498), (590, 498), (632, 556)], fill=(170, 210, 236))
    for cx in (360, 620):
        d.ellipse([cx - 52, 690, cx + 52, 794], fill=(30, 30, 34))
        d.ellipse([cx - 22, 720, cx + 22, 764], fill=(180, 184, 190))
    return im


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    makers = [exterior, living_room, kitchen, bedroom, balcony, parking]
    names = ["01_exterior", "02_living_room", "03_kitchen", "04_bedroom", "05_balcony", "06_parking"]
    for fn, name in zip(makers, names):
        fn().save(OUT / f"{name}.jpg", quality=92)
        print("saved", name)
