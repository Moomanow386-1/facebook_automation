"""
Compose a 1080×1350 image: photo fills full canvas, dark gradient fades in from
middle downward so text area is readable with no hard block edge.
Returns BytesIO or None on failure.
"""
import colorsys
import io
import math
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

CANVAS_W, CANVAS_H = 1080, 1350

GRADIENT_START_Y = 750   # gradient begins here (fully transparent)
GRADIENT_END_Y   = 1050  # fully opaque by this point
MAX_ALPHA = 245          # peak opacity of the overlay (0-255)

WHITE          = (255, 255, 255)
SUBTITLE_COLOR = (220, 220, 220)
ACCENT_COLOR   = (255, 107, 53)
ACCENT_BAR_W   = 6

FONT_BOLD    = "fonts/Prompt-Bold.ttf"
FONT_REGULAR = "fonts/Prompt-Regular.ttf"
LOGO_PATH    = "logo.jpg"
LOGO_SIZE    = 78    # px, square
LOGO_MARGIN  = 28    # px from edges

HEADLINE_SIZE   = 64
SUBTITLE_SIZE   = 38
PADDING_X       = 56
TEXT_START_Y    = 980   # where headline begins (well into the opaque zone)

# Thai combining chars (non-spacing marks) — must not start or end a line unit
_THAI_NON_STARTER = frozenset(
    "ั"                                    # ั mai han akat
    "ิีึืฺุู"  # ิ ี ึ ื ุ ู ฺ
    "็่้๊๋์ํ๎"  # ็ ่ ้ ๊ ๋ ์ ํ ๎
)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale + center-crop to fill target dimensions.

    For landscape sources (src ratio > target ratio by >15%), uses a blurred
    background so the sharp image fits full-width without heavy side-cropping.
    """
    iw, ih = img.size
    src_ratio = iw / ih
    tgt_ratio = target_w / target_h

    if src_ratio > tgt_ratio * 1.15:
        # Landscape→portrait: fit width, blur-fill vertical space
        scale_fg = target_w / iw
        fg_w = target_w
        fg_h = math.ceil(ih * scale_fg)

        # Blurred background: scale to fill height, crop width, then blur+darken
        scale_bg = target_h / ih
        bg_w = math.ceil(iw * scale_bg)
        bg = img.resize((bg_w, target_h), Image.LANCZOS)
        bg_left = (bg_w - target_w) // 2
        bg = bg.crop((bg_left, 0, bg_left + target_w, target_h))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
        bg = ImageEnhance.Brightness(bg).enhance(0.35)

        fg = img.resize((fg_w, fg_h), Image.LANCZOS)
        top_offset = (target_h - fg_h) // 2
        result = bg.convert("RGBA")
        result.paste(fg.convert("RGBA"), (0, top_offset))
        return result

    # Portrait/square: fill and center-crop (original behavior)
    scale = max(target_w / iw, target_h / ih)
    new_w, new_h = math.ceil(iw * scale), math.ceil(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _last_safe_break(s: str) -> int:
    """Return the rightmost index in s where breaking BEFORE s[i] is Thai-safe.

    Strict: neither s[i] nor s[i-1] is a combining char (preserves syllable boundaries).
    Falls back to relaxed: at least s[i] is not combining (avoids orphan diacritics).
    Returns 0 when no safe break exists (force-break caller's responsibility).
    """
    # Strict pass: preserve full syllable cluster
    for i in range(len(s) - 1, 0, -1):
        if s[i] not in _THAI_NON_STARTER and s[i - 1] not in _THAI_NON_STARTER:
            return i
    # Relaxed pass: at minimum avoid starting new line with combining char
    for i in range(len(s) - 1, 0, -1):
        if s[i] not in _THAI_NON_STARTER:
            return i
    return 0


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-split first; char-level fallback for long tokens with Thai syllable-safe breaking."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        if draw.textlength(test, font=font) <= max_width:
            current = test
        elif draw.textlength(word, font=font) > max_width:
            # Token wider than one line — char-level split with Thai safety
            if current:
                lines.append(current)
                current = ""
            for ch in word:
                probe = current + ch
                if draw.textlength(probe, font=font) <= max_width:
                    current = probe
                else:
                    bp = _last_safe_break(current)
                    if bp > 0:
                        lines.append(current[:bp])
                        carry = current[bp:]
                        # Try carry + ch; if still too wide, emit carry separately
                        if draw.textlength(carry + ch, font=font) <= max_width:
                            current = carry + ch
                        else:
                            if carry:
                                lines.append(carry)
                            current = ch
                    elif current:
                        lines.append(current)
                        current = ch
                    else:
                        lines.append(ch)
                        current = ""
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_headline(text: str, max_width: int, max_lines: int, draw: ImageDraw.ImageDraw) -> tuple[list[str], ImageFont.FreeTypeFont]:
    """Try decreasing font sizes until headline fits within max_lines. Returns (lines, font)."""
    for size in [64, 56, 50, 44]:
        font = _load_font(FONT_BOLD, size)
        lines = _wrap_text(text, font, max_width, draw)
        if len(lines) <= max_lines:
            return lines, font
    return lines, font  # best effort with smallest size


def _accent_color(photo: Image.Image) -> tuple[int, int, int]:
    """Pick the most saturated color from the bright zone of the photo, boosted for visibility."""
    h = photo.height
    strip = photo.crop((0, 0, photo.width, int(h * 0.65))).convert("RGB")
    strip = strip.resize((32, 24), Image.LANCZOS)
    pixels = list(strip.getdata())
    best_h, best_s, best_v = None, -1.0, 1.0
    for r, g, b in pixels:
        hv, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > best_s:
            best_s, best_h, best_v = s, hv, v
    if best_h is None or best_s < 0.25:
        return (255, 107, 53)  # fallback orange
    s = min(1.0, best_s * 1.15)
    v = max(0.88, best_v)
    r, g, b = colorsys.hsv_to_rgb(best_h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


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

        # Sample colors from photo
        tint   = _overlay_color(photo)
        accent = _accent_color(photo)

        # Build smooth gradient overlay — transparent at top, opaque at bottom
        # Uses t**2.0 easing so the gradient stays nearly invisible near the start
        # and ramps up naturally, avoiding a "solid block" appearance.
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)

        fade_steps = GRADIENT_END_Y - GRADIENT_START_Y
        for i in range(fade_steps):
            t = i / fade_steps
            alpha = int(MAX_ALPHA * (t ** 2.0))
            y = GRADIENT_START_Y + i
            ov_draw.rectangle([(0, y), (CANVAS_W, y + 1)], fill=(*tint, alpha))

        # Below gradient end: solid at MAX_ALPHA
        ov_draw.rectangle(
            [(0, GRADIENT_END_Y), (CANVAS_W, CANVAS_H)],
            fill=(*tint, MAX_ALPHA),
        )

        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)

        text_x     = PADDING_X
        text_max_w = CANVAS_W - PADDING_X * 2
        y          = TEXT_START_Y

        # Headline: auto-shrink until fits in 4 lines
        h_lines, h_font = _fit_headline(headline, text_max_w, 4, draw)
        h_size   = h_font.size
        line_h   = h_size + 12
        for line in h_lines:
            draw.text((text_x, y), line, font=h_font, fill=WHITE)
            y += line_h

        y += 20

        # Horizontal accent line
        draw.rectangle([(text_x, y), (text_x + 220, y + 5)], fill=accent)
        y += 26

        # Subtitle: fit as many lines as space allows (safety margin on width)
        s_font     = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
        s_line_h   = SUBTITLE_SIZE + 10
        sub_max_w  = int(text_max_w * 0.94)  # slight margin so long lines don't clip
        space_left = CANVAS_H - y - 20       # 20px bottom padding
        max_s_lines = max(1, space_left // s_line_h)

        s_lines = _wrap_text(subtitle, s_font, sub_max_w, draw)[:max_s_lines]
        for line in s_lines:
            draw.text((text_x, y), line, font=s_font, fill=SUBTITLE_COLOR)
            y += s_line_h

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
