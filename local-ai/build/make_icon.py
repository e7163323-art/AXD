"""יוצר אייקון לתוכנה (assets/gaon.ico)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for i in range(size // 2, 0, -1):
    t = i / (size / 2)
    color = (int(43 + 60 * (1 - t)), int(108 + 40 * (1 - t)), 246, 255)
    d.ellipse([size / 2 - i, size / 2 - i, size / 2 + i, size / 2 + i], fill=color)
font = None
for name in ("C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
    try:
        font = ImageFont.truetype(name, 110)
        break
    except OSError:
        continue
font = font or ImageFont.load_default()
d.text((size / 2, size / 2), "AI", fill="white", font=font, anchor="mm")
out = Path(__file__).resolve().parent.parent / "assets" / "gaon.ico"
out.parent.mkdir(exist_ok=True)
img.save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon:", out)
