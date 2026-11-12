"""Thumbnail generator (Pillow).

1280x720 YouTube thumbnail: vertical gradient background, a bold title
(wrapped to fit), an accent bar, and an optional subtitle line.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720

# (top colour, bottom colour) gradient pairs.
GRADIENTS = {
    "dark": ((18, 18, 28), (58, 28, 110)),
    "ocean": ((8, 60, 90), (10, 140, 150)),
    "ember": ((90, 20, 10), (200, 90, 10)),
    "forest": ((10, 60, 30), (20, 120, 70)),
}

ACCENT = (255, 176, 0)  # amber accent bar / highlight


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.split("\n"):
        words = raw_line.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def make_thumbnail(
    title: str,
    output_path: str,
    subtitle: str | None = None,
    gradient: str = "dark",
) -> dict:
    """Render a 1280x720 thumbnail PNG.

    Returns ``{"path", "size", "gradient"}``.
    """
    title = title.strip()
    if not title:
        raise ValueError("title must not be empty")
    top, bottom = GRADIENTS.get(gradient, GRADIENTS["dark"])

    img = Image.new("RGB", (WIDTH, HEIGHT), top)
    px = img.load()
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        colour = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        for x in range(WIDTH):
            px[x, y] = colour
    draw = ImageDraw.Draw(img)

    # Accent bar on the left.
    draw.rectangle([0, 0, 18, HEIGHT], fill=ACCENT)

    title_font = _load_font(96)
    lines = _wrap(draw, title.upper(), title_font, WIDTH - 160)
    while len(lines) > 3 and title_font.size > 48:
        title_font = _load_font(title_font.size - 8)
        lines = _wrap(draw, title.upper(), title_font, WIDTH - 160)
    lines = lines[:3]

    line_height = int(title_font.size * 1.15)
    block_height = line_height * len(lines)
    y = (HEIGHT - block_height) // 2 - (40 if subtitle else 0)
    for line in lines:
        draw.text((80, y), line, font=title_font, fill=(255, 255, 255),
                  stroke_width=3, stroke_fill=(0, 0, 0))
        y += line_height

    if subtitle:
        sub_font = _load_font(44, bold=False)
        draw.text((80, y + 30), subtitle, font=sub_font, fill=(255, 220, 120),
                  stroke_width=2, stroke_fill=(0, 0, 0))

    img.save(output_path, "PNG")
    return {"path": output_path, "size": (WIDTH, HEIGHT), "gradient": gradient}
