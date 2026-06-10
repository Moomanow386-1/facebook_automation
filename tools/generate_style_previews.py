"""
Generate preview images for all image_overlay style variants.
Saves: preview_style_0_original.jpg through preview_style_5_h_accent.jpg
"""
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
sys.path.insert(0, BASE_DIR)

CANVAS_W, CANVAS_H = 1080, 1350
FONT_BOLD    = os.path.join(BASE_DIR, "fonts", "Prompt-Bold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "fonts", "Prompt-Regular.ttf")
LOGO_PATH    = os.path.join(BASE_DIR, "logo.jpg")
LOGO_SIZE    = 78
LOGO_MARGIN  = 28

GRADIENT_START_Y = 700
GRADIENT_END_Y   = 1050
MAX_ALPHA        = 231

WHITE          = (255, 255, 255)
SUBTITLE_COLOR = (220, 220, 220)
ACCENT_COLOR   = (255, 107, 53)
ACCENT_BAR_W   = 6
HEADLINE_SIZE  = 72
SUBTITLE_SIZE  = 38
PADDING_X      = 56
TEXT_START_Y   = 980

TEST_HEADLINE = "AI Agents ปฏิวัติการทำงาน ในปี 2025"
TEST_SUBTITLE = "บริษัทใหญ่แห่กัน deploy agent หลายพันตัว ทั่วโลก"
TEST_TOPIC    = "AI AGENTS"


def _load_font(path, size):
    return ImageFont.truetype(path, size)


def _wrap_text(text, font, max_width, draw):
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


def _overlay_color(photo):
    h = photo.height
    strip = photo.crop((0, int(h * 0.7), photo.width, h)).convert("RGB")
    strip = strip.resize((16, 4), Image.LANCZOS)
    pixels = list(strip.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (int(r * 0.25), int(g * 0.25), int(b * 0.25))


def _build_gradient(tint, start_y=GRADIENT_START_Y, end_y=GRADIENT_END_Y, max_alpha=MAX_ALPHA):
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    fade_steps = end_y - start_y
    for i in range(fade_steps):
        t = i / fade_steps
        alpha = int(max_alpha * (t ** 0.55))
        ov_draw.rectangle([(0, start_y + i), (CANVAS_W, start_y + i + 1)], fill=(*tint, alpha))
    ov_draw.rectangle([(0, end_y), (CANVAS_W, CANVAS_H)], fill=(*tint, max_alpha))
    return overlay


def _add_logo(canvas, top_left=False):
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
        lx = LOGO_MARGIN if top_left else CANVAS_W - LOGO_SIZE - LOGO_MARGIN
        ly = LOGO_MARGIN if top_left else CANVAS_H - LOGO_SIZE - LOGO_MARGIN
        canvas.paste(logo, (lx, ly), logo)
    except Exception as e:
        print(f"  [logo skipped: {e}]")


def make_test_photo(palette: str = "blue") -> Image.Image:
    """Synthetic background with different color palettes for testing."""
    palettes = {
        "blue":   {"top": (10, 20, 80),  "bot": (20, 60, 160), "blobs": [(40, 80, 200), (10, 120, 180), (50, 40, 140)]},
        "green":  {"top": (5,  40, 20),  "bot": (20, 120, 50), "blobs": [(30, 160, 60), (10, 100, 80),  (40, 80,  30)]},
        "red":    {"top": (80, 10, 10),  "bot": (160, 40, 20), "blobs": [(200, 60, 30), (140, 20, 60),  (100, 50, 10)]},
        "purple": {"top": (40, 10, 80),  "bot": (80, 20, 160), "blobs": [(100, 40, 200),(60, 10, 140),  (80, 50, 120)]},
        "teal":   {"top": (5,  50, 60),  "bot": (10, 130, 140),"blobs": [(20, 160, 170),(10, 100, 120), (30, 80, 100)]},
        "gold":   {"top": (80, 50, 5),   "bot": (160, 120, 10),"blobs": [(200, 150, 20),(140, 100, 10), (100, 80, 30)]},
    }
    p = palettes.get(palette, palettes["blue"])
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H))
    draw = ImageDraw.Draw(img)
    for y in range(CANVAS_H):
        t = y / CANVAS_H
        r = int(p["top"][0] * (1 - t) + p["bot"][0] * t)
        g = int(p["top"][1] * (1 - t) + p["bot"][1] * t)
        b = int(p["top"][2] * (1 - t) + p["bot"][2] * t)
        draw.rectangle([(0, y), (CANVAS_W, y + 1)], fill=(r, g, b, 255))
    blobs = [(150, 60, 720, 560), (480, 280, 980, 740), (80, 580, 520, 960)]
    for (x0, y0, x1, y1), col in zip(blobs, p["blobs"]):
        draw.ellipse([x0, y0, x1, y1], fill=(*col, 130))
    return img


# ─── Style 0: Original (current design) ──────────────────────────────────────

def style_0_original(photo, headline, subtitle, topic):
    canvas = photo.copy()
    tint = _overlay_color(photo)
    canvas = Image.alpha_composite(canvas, _build_gradient(tint))
    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2
    y = TEXT_START_Y
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:4]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 20
    draw.rectangle([(text_x, y), (text_x + 220, y + 5)], fill=ACCENT_COLOR)
    y += 26
    s_lines = _wrap_text(subtitle, s_font, text_max_w, draw)[:3]
    for line in s_lines:
        draw.text((text_x, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 1: Category Chip ───────────────────────────────────────────────────

def style_1_chip(photo, headline, subtitle, topic):
    """Colored pill badge above the headline with topic label."""
    canvas = photo.copy()
    tint = _overlay_color(photo)
    canvas = Image.alpha_composite(canvas, _build_gradient(tint, start_y=660))
    draw = ImageDraw.Draw(canvas)
    h_font   = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font   = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    chip_font = _load_font(FONT_BOLD, 30)
    text_x   = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2

    y = TEXT_START_Y - 90

    # Pill chip
    chip_pad_x, chip_pad_y = 22, 8
    chip_text_w = int(draw.textlength(topic, font=chip_font))
    pill_w = chip_text_w + chip_pad_x * 2
    pill_h = 30 + chip_pad_y * 2
    draw.rounded_rectangle(
        [(text_x, y), (text_x + pill_w, y + pill_h)],
        radius=pill_h // 2,
        fill=ACCENT_COLOR,
    )
    draw.text((text_x + chip_pad_x, y + chip_pad_y), topic, font=chip_font, fill=WHITE)
    y += pill_h + 16

    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:3]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 18

    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:2]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)
    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 2: Brand-color gradient ───────────────────────────────────────────

def style_2_brand_gradient(photo, headline, subtitle, topic):
    """Gradient shifts from brand orange → near-black instead of dynamic photo tint."""
    canvas = photo.copy()
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    fade_steps = GRADIENT_END_Y - GRADIENT_START_Y
    for i in range(fade_steps):
        t = i / fade_steps
        alpha = int(MAX_ALPHA * (t ** 0.55))
        r = int(255 * (1 - t) + 20 * t)
        g = int(80  * (1 - t) + 10 * t)
        b = int(20  * (1 - t) + 5  * t)
        ov_draw.rectangle([(0, GRADIENT_START_Y + i), (CANVAS_W, GRADIENT_START_Y + i + 1)],
                          fill=(r, g, b, alpha))
    ov_draw.rectangle([(0, GRADIENT_END_Y), (CANVAS_W, CANVAS_H)], fill=(20, 10, 5, MAX_ALPHA))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2
    y = TEXT_START_Y
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:4]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 22
    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:3]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)
    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 3: Blur zone ───────────────────────────────────────────────────────

def style_3_blur(photo, headline, subtitle, topic):
    """Photo gradually blurs in gradient zone so text area feels glassy."""
    blurred = photo.filter(ImageFilter.GaussianBlur(radius=14))
    mask = Image.new("L", (CANVAS_W, CANVAS_H), 0)
    mask_draw = ImageDraw.Draw(mask)
    fade_h = 120
    for i in range(fade_h):
        val = int(255 * (i / fade_h))
        mask_draw.rectangle([(0, GRADIENT_START_Y + i), (CANVAS_W, GRADIENT_START_Y + i + 1)],
                            fill=val)
    mask_draw.rectangle([(0, GRADIENT_START_Y + fade_h), (CANVAS_W, CANVAS_H)], fill=255)
    # composite: mask=0 → photo sharp, mask=255 → blurred
    canvas = Image.composite(blurred, photo, mask).convert("RGBA")
    tint = _overlay_color(photo)
    canvas = Image.alpha_composite(canvas, _build_gradient(tint))
    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2
    y = TEXT_START_Y
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:4]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 22
    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:3]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)
    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 4: Tagline strip ───────────────────────────────────────────────────

def style_4_strip(photo, headline, subtitle, topic):
    """Solid brand-color bar at bottom with page name. Logo moves to top-left."""
    STRIP_H = 60
    canvas = photo.copy()
    tint = _overlay_color(photo)
    canvas = Image.alpha_composite(canvas, _build_gradient(tint, start_y=660, end_y=1010))

    strip_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ImageDraw.Draw(strip_layer).rectangle(
        [(0, CANVAS_H - STRIP_H), (CANVAS_W, CANVAS_H)],
        fill=(*ACCENT_COLOR, 255),
    )
    canvas = Image.alpha_composite(canvas, strip_layer)

    draw = ImageDraw.Draw(canvas)
    strip_font = _load_font(FONT_BOLD, 30)
    page_label = "AI TODAY"
    lw = draw.textlength(page_label, font=strip_font)
    draw.text(
        ((CANVAS_W - lw) // 2, CANVAS_H - STRIP_H + (STRIP_H - 30) // 2),
        page_label, font=strip_font, fill=WHITE,
    )

    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2
    y = TEXT_START_Y - 70
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:3]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 18
    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:2]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)
    _add_logo(canvas, top_left=True)
    return canvas


# ─── Style 5: Horizontal accent line ─────────────────────────────────────────

def style_5_h_accent(photo, headline, subtitle, topic):
    """Replace vertical accent bar with a short horizontal line under headline."""
    canvas = photo.copy()
    tint = _overlay_color(photo)
    canvas = Image.alpha_composite(canvas, _build_gradient(tint))
    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2
    y = TEXT_START_Y
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:4]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 20
    # Horizontal accent line
    draw.rectangle([(text_x, y), (text_x + 220, y + 5)], fill=ACCENT_COLOR)
    y += 26
    s_lines = _wrap_text(subtitle, s_font, text_max_w, draw)[:3]
    for line in s_lines:
        draw.text((text_x, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 6: Split Card ─────────────────────────────────────────────────────

def style_6_split_card(photo, headline, subtitle, topic):
    """Top half = photo, bottom half = solid dark card with text."""
    SPLIT_Y = CANVAS_H // 2  # 675px
    CARD_COLOR = (18, 18, 22)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (*CARD_COLOR, 255))

    # Photo fills top half
    photo_top = photo.crop((0, 0, CANVAS_W, SPLIT_Y))
    canvas.paste(photo_top.convert("RGBA"), (0, 0))

    # Thin accent line at split
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, SPLIT_Y), (CANVAS_W, SPLIT_Y + 5)], fill=ACCENT_COLOR)

    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2

    y = SPLIT_Y + 52
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:3]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 24

    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:2]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)

    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 7: Left Panel ──────────────────────────────────────────────────────

def style_7_left_panel(photo, headline, subtitle, topic):
    """Left 42% = dark panel with text, right 58% = photo."""
    PANEL_W = int(CANVAS_W * 0.42)
    PANEL_COLOR = (14, 14, 18)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (*PANEL_COLOR, 255))

    # Photo on right side
    photo_right = photo.crop((0, 0, CANVAS_W - PANEL_W, CANVAS_H))
    canvas.paste(photo_right.convert("RGBA"), (PANEL_W, 0))

    # Subtle gradient on left edge of photo to blend into panel
    blend = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blend)
    for i in range(80):
        alpha = int(255 * (1 - i / 80))
        bd.rectangle([(PANEL_W + i, 0), (PANEL_W + i + 1, CANVAS_H)],
                     fill=(*PANEL_COLOR, alpha))
    canvas = Image.alpha_composite(canvas, blend)

    draw = ImageDraw.Draw(canvas)

    # Accent bar at top of panel
    draw.rectangle([(0, 0), (6, CANVAS_H)], fill=ACCENT_COLOR)

    h_font  = _load_font(FONT_BOLD, 58)
    s_font  = _load_font(FONT_REGULAR, 30)
    text_x  = 24
    text_max_w = PANEL_W - text_x - 16

    y = 120
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:5]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += 58 + 10
    y += 28

    draw.rectangle([(text_x, y), (text_x + 40, y + 4)], fill=ACCENT_COLOR)
    y += 22

    s_lines = _wrap_text(subtitle, s_font, text_max_w, draw)[:4]
    for line in s_lines:
        draw.text((text_x, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += 30 + 8

    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 8: Top Banner ──────────────────────────────────────────────────────

def style_8_top_banner(photo, headline, subtitle, topic):
    """Gradient at TOP (text area up top), photo fills bottom portion."""
    BANNER_H = 520
    TINT = (12, 12, 18)

    canvas = photo.copy()

    # Top gradient: opaque at top, transparent toward banner bottom
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    fade_start = BANNER_H - 160
    ov_draw.rectangle([(0, 0), (CANVAS_W, fade_start)], fill=(*TINT, MAX_ALPHA))
    for i in range(160):
        t = i / 160
        alpha = int(MAX_ALPHA * (1 - t ** 0.55))
        ov_draw.rectangle([(0, fade_start + i), (CANVAS_W, fade_start + i + 1)],
                          fill=(*TINT, alpha))
    canvas = Image.alpha_composite(canvas, overlay)

    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
    s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
    text_x    = PADDING_X
    text_max_w = CANVAS_W - PADDING_X * 2

    y = 72
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:3]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += HEADLINE_SIZE + 12
    y += 22

    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 16, draw)[:2]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 16, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += SUBTITLE_SIZE + 10
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)

    _add_logo(canvas, top_left=False)
    return canvas


# ─── Style 9: Framed Overlay ──────────────────────────────────────────────────

def style_9_framed(photo, headline, subtitle, topic):
    """Brand-color border frame + frosted text panel floating over photo."""
    FRAME = 22
    PANEL_MARGIN = 40
    PANEL_H = 340

    canvas = photo.copy()

    # Frame border
    frame_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame_layer)
    fd.rectangle([(0, 0), (CANVAS_W, FRAME)], fill=(*ACCENT_COLOR, 255))
    fd.rectangle([(0, CANVAS_H - FRAME), (CANVAS_W, CANVAS_H)], fill=(*ACCENT_COLOR, 255))
    fd.rectangle([(0, 0), (FRAME, CANVAS_H)], fill=(*ACCENT_COLOR, 255))
    fd.rectangle([(CANVAS_W - FRAME, 0), (CANVAS_W, CANVAS_H)], fill=(*ACCENT_COLOR, 255))
    canvas = Image.alpha_composite(canvas, frame_layer)

    # Frosted glass panel
    panel_y = CANVAS_H - FRAME - PANEL_MARGIN - PANEL_H
    panel_x = FRAME + PANEL_MARGIN

    # Blur the photo region behind panel
    region = canvas.crop((panel_x, panel_y,
                          CANVAS_W - FRAME - PANEL_MARGIN,
                          panel_y + PANEL_H))
    region = region.filter(ImageFilter.GaussianBlur(radius=20))
    canvas.paste(region.convert("RGBA"), (panel_x, panel_y))

    # Semi-transparent dark tint over blurred area
    panel_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ImageDraw.Draw(panel_layer).rectangle(
        [(panel_x, panel_y), (CANVAS_W - FRAME - PANEL_MARGIN, panel_y + PANEL_H)],
        fill=(10, 10, 15, 200),
    )
    canvas = Image.alpha_composite(canvas, panel_layer)

    draw = ImageDraw.Draw(canvas)
    h_font = _load_font(FONT_BOLD, 62)
    s_font = _load_font(FONT_REGULAR, 34)
    text_x    = panel_x + 30
    text_max_w = CANVAS_W - FRAME - PANEL_MARGIN - panel_x - 60

    y = panel_y + 30
    h_lines = _wrap_text(headline, h_font, text_max_w, draw)[:2]
    for line in h_lines:
        draw.text((text_x, y), line, font=h_font, fill=WHITE)
        y += 62 + 10
    y += 16

    s_lines = _wrap_text(subtitle, s_font, text_max_w - ACCENT_BAR_W - 14, draw)[:2]
    accent_top = y
    for line in s_lines:
        draw.text((text_x + ACCENT_BAR_W + 14, y), line, font=s_font, fill=SUBTITLE_COLOR)
        y += 34 + 8
    draw.rectangle([(text_x, accent_top), (text_x + ACCENT_BAR_W, y)], fill=ACCENT_COLOR)

    _add_logo(canvas, top_left=True)
    return canvas


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--multi" in sys.argv:
        # Generate style_0 (new design) across 6 color palettes to preview dynamic accent
        from image_overlay import _accent_color, _overlay_color

        for pal in ["blue", "green", "red", "purple", "teal", "gold"]:
            print(f"Rendering multi_{pal}...")
            photo = make_test_photo(pal)
            canvas = photo.copy()
            tint   = _overlay_color(photo)
            accent = _accent_color(photo)
            print(f"  accent RGB = {accent}")
            canvas = Image.alpha_composite(canvas, _build_gradient(tint))
            draw = ImageDraw.Draw(canvas)
            h_font = _load_font(FONT_BOLD, HEADLINE_SIZE)
            s_font = _load_font(FONT_REGULAR, SUBTITLE_SIZE)
            text_x = PADDING_X
            text_max_w = CANVAS_W - PADDING_X * 2
            y = TEXT_START_Y
            for line in _wrap_text(TEST_HEADLINE, h_font, text_max_w, draw)[:4]:
                draw.text((text_x, y), line, font=h_font, fill=WHITE)
                y += HEADLINE_SIZE + 12
            y += 20
            draw.rectangle([(text_x, y), (text_x + 220, y + 5)], fill=accent)
            y += 26
            for line in _wrap_text(TEST_SUBTITLE, s_font, text_max_w, draw)[:3]:
                draw.text((text_x, y), line, font=s_font, fill=SUBTITLE_COLOR)
                y += SUBTITLE_SIZE + 10
            _add_logo(canvas)
            out = f"preview_multi_{pal}.jpg"
            canvas.convert("RGB").save(out, format="JPEG", quality=92)
            print(f"  -> {out}")
        print("Done -- 6 multi-bg previews saved.")
        sys.exit(0)

    print("Building test photo...")
    test_photo = make_test_photo()

    styles = [
        ("0_original",   style_0_original),
        ("1_chip",       style_1_chip),
        ("2_brand_grad", style_2_brand_gradient),
        ("3_blur",       style_3_blur),
        ("4_strip",      style_4_strip),
        ("5_h_accent",   style_5_h_accent),
        ("6_split_card", style_6_split_card),
        ("7_left_panel", style_7_left_panel),
        ("8_top_banner", style_8_top_banner),
        ("9_framed",     style_9_framed),
    ]

    for name, fn in styles:
        print(f"Rendering style_{name}...")
        result = fn(test_photo.copy(), TEST_HEADLINE, TEST_SUBTITLE, TEST_TOPIC)
        out = f"preview_style_{name}.jpg"
        result.convert("RGB").save(out, format="JPEG", quality=92)
        print(f"  -> {out}")

    print("Done -- 10 previews saved.")
