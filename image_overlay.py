"""
Compose a 1080×1350 image: photo fills full canvas, dark gradient fades in from
middle downward so text area is readable with no hard block edge.
Returns BytesIO or None on failure.
"""
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1350

GRADIENT_START_Y = 700   # gradient begins here (fully transparent)
GRADIENT_END_Y   = 1050  # fully opaque by this point
MAX_ALPHA = 231          # peak opacity of the overlay (0-255)

WHITE          = (255, 255, 255)
SUBTITLE_COLOR = (220, 220, 220)
ACCENT_COLOR   = (255, 107, 53)
ACCENT_BAR_W   = 6

FONT_BOLD    = "fonts/Prompt-Bold.ttf"
FONT_REGULAR = "fonts/Prompt-Regular.ttf"
LOGO_PATH    = "logo.jpg"
LOGO_SIZE    = 78    # px, square
LOGO_MARGIN  = 28    # px from edges

HEADLINE_SIZE   = 72
SUBTITLE_SIZE   = 38
PADDING_X       = 56
TEXT_START_Y    = 980   # where headline begins (well into the opaque zone)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale + center-crop to fill target dimensions exactly."""
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    new_w, new_h = math.ceil(iw * scale), math.ceil(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-split first, then char-level fallback for long Thai tokens."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        if draw.textlength(test, font=font) <= max_width:
            current = test
        elif draw.textlength(word, font=font) > max_width:
            if current:
                lines.append(current)
                current = ""
            for ch in word:
                probe = current + ch
                if draw.textlength(probe, font=font) <= max_width:
                    current = probe
                else:
                    lines.append(current)
                    current = ch
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _overlay_color(photo: Image.Image) -> tuple[int, int, int]:
    """Sample bottom third of photo and darken for overlay tint."""
    h = photo.height
    strip = photo.crop((0, int(h * 0.7), photo.width, h)).convert("RGB")
    strip = strip.resize((16, 4), Image.LANCZOS)
    pixels = list(strip.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    factor = 0.25
    return (int(r * factor), int(g * factor), int(b * factor))


def compose(image_url: str, headline: str, subtitle: str) -> io.BytesIO | None:
    """Download OG image and compose the overlay. Returns BytesIO (JPEG) or None."""
    try:
        resp = requests.get(image_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        og = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"[overlay] image download failed: {e}")
        return None

    try:
        # Photo fills the entire canvas
        photo = _fit_image(og, CANVAS_W, CANVAS_H).convert("RGBA")
        canvas = photo.copy()

        # Sample color for overlay tint
        tint = _overlay_color(photo)

        # Build smooth gradient overlay — transparent at top, opaque at bottom
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)

        fade_steps = GRADIENT_END_Y - GRADIENT_START_Y
        for i in range(fade_steps):
            t = i / fade_steps
            alpha = int(MAX_ALPHA * (t ** 0.55))  # smooth ease-in
            y = GRADIENT_START_Y + i
            ov_draw.rectangle([(0, y), (CANVAS_W, y + 1)], fill=(*tint, alpha))

        # Below gradient end: solid at MAX_ALPHA
        ov_draw.rectangle(
            [(0, GRADIENT_END_Y), (CANVAS_W, CANVAS_H)],
            fill=(*tint, MAX_ALPHA),
        )

        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)

        # Load fonts
        h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
        s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)

        text_x   = PADDING_X
        text_max_w = CANVAS_W - PADDING_X * 2
        y = TEXT_START_Y

        # Headline (max 4 lines)
        h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:4]
        line_h = HEADLINE_SIZE + 12
        for line in h_lines:
            draw.text((text_x, y), line, font=h_font, fill=WHITE)
            y += line_h

        y += 22

        # Accent bar + subtitle (max 3 lines)
        s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:3]
        s_line_h = SUBTITLE_SIZE + 10
        accent_top = y
        for line in s_lines:
            draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
            y += s_line_h
        draw.rectangle(
            [(text_x, accent_top), (text_x + ACCENT_BAR_W, y)],
            fill=ACCENT_COLOR,
        )

        # Watermark logo — bottom right
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            lx = CANVAS_W - LOGO_SIZE - LOGO_MARGIN
            ly = CANVAS_H - LOGO_SIZE - LOGO_MARGIN
            canvas.paste(logo, (lx, ly), logo)
        except Exception as e:
            print(f"[overlay] logo skipped: {e}")

        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=92)
        buf.seek(0)
        return buf

    except Exception as e:
        print(f"[overlay] compose failed: {e}")
        return None
