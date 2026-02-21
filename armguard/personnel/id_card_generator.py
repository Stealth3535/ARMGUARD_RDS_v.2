"""
Personnel ID Card Generator
===========================
Generates a standard CR80 (3.375" × 2.125" @ 300 DPI = 1013 × 638 px) ID card
for each registered personnel.

Outputs a single PNG with both sides rendered side-by-side:
  <personnel_id>_front.png  — left half (front)
  <personnel_id>_back.png   — right half (back)
  <personnel_id>.png         — combined (both sides, 2026 × 638 px)

All files saved to:  core/media/personnel_id_cards/
"""

import os
import io
import logging

from PIL import Image, ImageDraw, ImageFilter, ImageOps
import qrcode
from qrcode.image.pil import PilImage
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Card dimensions  (CR80  @ 300 DPI)
# ---------------------------------------------------------------------------
CARD_W = 1013
CARD_H = 638

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
NAVY          = "#1a3560"        # Header bar background / accent
WHITE         = "#FFFFFF"
DARK_TEXT     = "#0f172a"        # Names / ID values
SUBTEXT       = "#475569"        # Serial / caption
LIGHT_BG      = "#f0f5ff"        # Card background tint
PILL_BG       = "#dbeafe"        # Classification badge fill
PILL_TEXT     = "#1e40af"        # Classification badge text
FOOTER_LABEL  = "#94a3b8"        # "PERSONNEL ID" caption
FOOTER_VAL    = "#0f172a"        # Personnel ID value
DIVIDER       = "#cbd5e1"        # Thin separator lines
PHOTO_BORDER  = "#cbd5e1"

# ---------------------------------------------------------------------------
# Helper: load a TrueType font with fallback to default bitmap font
# ---------------------------------------------------------------------------
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    from PIL import ImageFont

    # Windows system fonts
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    font = None
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                break
            except (IOError, OSError):
                continue

    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


# ---------------------------------------------------------------------------
# Helper: draw centred text
# ---------------------------------------------------------------------------
def _draw_text_centred(draw, x_centre, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((x_centre - w // 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]   # height


# ---------------------------------------------------------------------------
# Helper: draw rounded rectangle (Pillow ≥ 8 supports radius)
# ---------------------------------------------------------------------------
def _rounded_rect(draw, xy, radius, fill, outline=None, outline_width=1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                            outline=outline, width=outline_width)


# ---------------------------------------------------------------------------
# Build FRONT card
# ---------------------------------------------------------------------------
def _build_front(personnel) -> Image.Image:
    card = Image.new("RGB", (CARD_W, CARD_H), LIGHT_BG)
    draw = ImageDraw.Draw(card)

    # --- subtle gradient-like background stripe ---
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(240 + (255 - 240) * t)
        g = int(245 + (255 - 245) * t)
        b = int(255)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))

    # --- Header bar ---
    HEADER_H = 74
    _rounded_rect(draw, (0, 0, CARD_W, HEADER_H), radius=0, fill=NAVY)
    # "ARMORY" bold  +  "CARD" thinner  in the header
    header_font_big  = _font(36, bold=True)
    header_font_sml  = _font(30, bold=False)
    # Measure combined width
    bb1 = draw.textbbox((0, 0), "ARMORY ", font=header_font_big)
    bb2 = draw.textbbox((0, 0), "CARD",   font=header_font_sml)
    total_w = (bb1[2] - bb1[0]) + (bb2[2] - bb2[0])
    x_start = (CARD_W - total_w) // 2
    y_txt   = (HEADER_H - (bb1[3] - bb1[1])) // 2
    draw.text((x_start, y_txt), "ARMORY ", font=header_font_big, fill=WHITE)
    draw.text((x_start + (bb1[2] - bb1[0]), y_txt + 4),
              "CARD", font=header_font_sml, fill="#a5c8f8")

    # --- Photo area (left column) ---
    PHOTO_SIZE   = 310          # square
    PHOTO_X      = 52
    PHOTO_Y      = HEADER_H + 30
    PHOTO_BORDER = 4

    # Frame
    _rounded_rect(draw,
                  (PHOTO_X - PHOTO_BORDER,
                   PHOTO_Y - PHOTO_BORDER,
                   PHOTO_X + PHOTO_SIZE + PHOTO_BORDER,
                   PHOTO_Y + PHOTO_SIZE + PHOTO_BORDER),
                  radius=10, fill=WHITE, outline=NAVY, outline_width=3)

    # Load & paste photo
    try:
        if personnel.picture and os.path.exists(personnel.picture.path):
            photo = Image.open(personnel.picture.path).convert("RGB")
            photo = ImageOps.fit(photo, (PHOTO_SIZE, PHOTO_SIZE), method=Image.LANCZOS)
        else:
            raise FileNotFoundError
    except Exception:
        # Placeholder – gray square with silhouette tint
        photo = Image.new("RGB", (PHOTO_SIZE, PHOTO_SIZE), "#dde3ee")
        ph_draw = ImageDraw.Draw(photo)
        ph_draw.ellipse([90, 40, 220, 170], fill="#b0bcd4")
        ph_draw.ellipse([60, 155, 250, 310], fill="#b0bcd4")

    card.paste(photo, (PHOTO_X, PHOTO_Y))

    # --- Right-side text column ---
    TEXT_X      = PHOTO_X + PHOTO_SIZE + PHOTO_BORDER + 30
    TEXT_W      = CARD_W - TEXT_X - 30
    TEXT_Y_START = HEADER_H + 36

    # Rank abbreviation badge (top-right corner)
    rank_abbr = (personnel.rank or "").upper()
    if rank_abbr:
        rb_font = _font(18, bold=True)
        rb_bbox = draw.textbbox((0, 0), rank_abbr, font=rb_font)
        rb_w    = rb_bbox[2] - rb_bbox[0] + 24
        rb_h    = rb_bbox[3] - rb_bbox[1] + 12
        rb_x    = CARD_W - rb_w - 26
        rb_y    = HEADER_H + 16
        _rounded_rect(draw, (rb_x, rb_y, rb_x + rb_w, rb_y + rb_h),
                      radius=8, fill=NAVY)
        draw.text((rb_x + 12, rb_y + 6), rank_abbr, font=rb_font, fill=WHITE)

    cur_y = TEXT_Y_START

    # Full name  (rank abbr + firstname + MI + surname)
    mi = (personnel.middle_initial or "").strip().rstrip(".")
    mi_str = f" {mi}." if mi else ""
    full_name = (
        f"{(personnel.rank or '').upper()} "
        f"{personnel.firstname.upper()}"
        f"{mi_str} "
        f"{personnel.surname.upper()}"
    ).strip()

    name_font = _font(34, bold=True)
    # Word-wrap if too wide
    words = full_name.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bb = draw.textbbox((0, 0), test, font=name_font)
        if bb[2] - bb[0] > TEXT_W and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    for line in lines:
        draw.text((TEXT_X, cur_y), line, font=name_font, fill=DARK_TEXT)
        bb = draw.textbbox((0, 0), line, font=name_font)
        cur_y += (bb[3] - bb[1]) + 6
    cur_y += 8

    # Serial line  "O-154068  ·  PAF"
    serial_str = f"{personnel.serial}  ·  PAF"
    serial_font = _font(26, bold=False)
    draw.text((TEXT_X, cur_y), serial_str, font=serial_font, fill=SUBTEXT)
    bb = draw.textbbox((0, 0), serial_str, font=serial_font)
    cur_y += (bb[3] - bb[1]) + 18

    # Classification pill
    classif = personnel.classification or "ENLISTED PERSONNEL"
    pill_text = classif.upper()
    pill_font = _font(22, bold=True)
    pb = draw.textbbox((0, 0), pill_text, font=pill_font)
    pill_w = pb[2] - pb[0] + 32
    pill_h = pb[3] - pb[1] + 16
    _rounded_rect(draw, (TEXT_X, cur_y, TEXT_X + pill_w, cur_y + pill_h),
                  radius=pill_h // 2, fill=PILL_BG)
    draw.text((TEXT_X + 16, cur_y + 8), pill_text, font=pill_font, fill=PILL_TEXT)
    cur_y += pill_h + 20

    # Group badge
    group_str = personnel.group or "HAS"
    grp_font = _font(20, bold=False)
    gb = draw.textbbox((0, 0), group_str, font=grp_font)
    grp_w = gb[2] - gb[0] + 24
    grp_h = gb[3] - gb[1] + 12
    _rounded_rect(draw, (TEXT_X, cur_y, TEXT_X + grp_w, cur_y + grp_h),
                  radius=6, fill="#e2e8f0")
    draw.text((TEXT_X + 12, cur_y + 6), group_str, font=grp_font, fill="#334155")

    # --- Footer ---
    FOOTER_H = 82
    footer_y  = CARD_H - FOOTER_H
    draw.line([(0, footer_y), (CARD_W, footer_y)], fill=NAVY, width=3)

    lbl_font = _font(18, bold=False)
    val_font = _font(24, bold=True)

    _draw_text_centred(draw, CARD_W // 2, footer_y + 10,
                       "PERSONNEL ID", lbl_font, FOOTER_LABEL)
    _draw_text_centred(draw, CARD_W // 2, footer_y + 34,
                       personnel.id, val_font, FOOTER_VAL)

    # Thin decorative line at bottom
    draw.rectangle([(0, CARD_H - 6), (CARD_W, CARD_H)], fill=NAVY)

    return card


# ---------------------------------------------------------------------------
# Build BACK card
# ---------------------------------------------------------------------------
def _build_back(personnel) -> Image.Image:
    card = Image.new("RGB", (CARD_W, CARD_H), WHITE)
    draw = ImageDraw.Draw(card)

    # Background tint
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(240 + (255 - 240) * t)
        g = int(245 + (255 - 245) * t)
        b = int(255)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))

    # --- Header (same as front) ---
    HEADER_H = 74
    _rounded_rect(draw, (0, 0, CARD_W, HEADER_H), radius=0, fill=NAVY)
    header_font_big = _font(36, bold=True)
    header_font_sml = _font(30, bold=False)
    bb1 = draw.textbbox((0, 0), "ARMORY ", font=header_font_big)
    bb2 = draw.textbbox((0, 0), "CARD",   font=header_font_sml)
    total_w = (bb1[2] - bb1[0]) + (bb2[2] - bb2[0])
    x_start = (CARD_W - total_w) // 2
    y_txt   = (HEADER_H - (bb1[3] - bb1[1])) // 2
    draw.text((x_start, y_txt), "ARMORY ", font=header_font_big, fill=WHITE)
    draw.text((x_start + (bb1[2] - bb1[0]), y_txt + 4),
              "CARD", font=header_font_sml, fill="#a5c8f8")

    # --- QR Code ---
    FOOTER_H = 82
    qr_area_top    = HEADER_H + 18
    qr_area_bottom = CARD_H - FOOTER_H - 14
    qr_size        = min(qr_area_bottom - qr_area_top, CARD_W - 120)
    qr_size        = qr_size - (qr_size % 2)   # ensure even

    qr_data = str(personnel.id)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)

    qr_x = (CARD_W - qr_size) // 2
    qr_y = qr_area_top + (qr_area_bottom - qr_area_top - qr_size) // 2

    # White frame around QR
    pad = 12
    _rounded_rect(draw,
                  (qr_x - pad, qr_y - pad,
                   qr_x + qr_size + pad, qr_y + qr_size + pad),
                  radius=10, fill=WHITE, outline=NAVY, outline_width=3)
    card.paste(qr_img, (qr_x, qr_y))

    # --- Footer (same layout as front) ---
    footer_y = CARD_H - FOOTER_H
    draw.line([(0, footer_y), (CARD_W, footer_y)], fill=NAVY, width=3)

    lbl_font = _font(18, bold=False)
    val_font = _font(24, bold=True)

    _draw_text_centred(draw, CARD_W // 2, footer_y + 10,
                       "PERSONNEL ID", lbl_font, FOOTER_LABEL)
    _draw_text_centred(draw, CARD_W // 2, footer_y + 34,
                       personnel.id, val_font, FOOTER_VAL)

    draw.rectangle([(0, CARD_H - 6), (CARD_W, CARD_H)], fill=NAVY)

    return card


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------
def generate_personnel_id_card(personnel) -> dict:
    """
    Generate front + back ID card PNGs for *personnel* and save them to
    ``core/media/personnel_id_cards/``.

    Returns a dict with keys:
        combined – relative media path of the combined PNG  (both sides)
        front    – relative media path of the front-only PNG
        back     – relative media path of the back-only PNG
    """
    media_root = settings.MEDIA_ROOT
    out_dir    = os.path.join(media_root, "personnel_id_cards")
    os.makedirs(out_dir, exist_ok=True)

    front = _build_front(personnel)
    back  = _build_back(personnel)

    pid = personnel.id  # e.g. "PO-154068180226"

    # Save individual sides
    front_path    = os.path.join(out_dir, f"{pid}_front.png")
    back_path     = os.path.join(out_dir, f"{pid}_back.png")
    combined_path = os.path.join(out_dir, f"{pid}.png")

    front.save(front_path, "PNG", dpi=(300, 300))
    back.save(back_path,   "PNG", dpi=(300, 300))

    # Combined side-by-side (2026 × 638)
    GAP = 20
    combined = Image.new("RGB", (CARD_W * 2 + GAP, CARD_H), "#e2e8f0")
    combined.paste(front, (0, 0))
    combined.paste(back,  (CARD_W + GAP, 0))
    combined.save(combined_path, "PNG", dpi=(300, 300))

    logger.info("ID card generated for personnel %s → %s", pid, combined_path)

    return {
        "combined": f"personnel_id_cards/{pid}.png",
        "front":    f"personnel_id_cards/{pid}_front.png",
        "back":     f"personnel_id_cards/{pid}_back.png",
    }
