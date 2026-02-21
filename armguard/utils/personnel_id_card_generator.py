"""
Personnel ID Card Generator  —  utils/personnel_id_card_generator.py
=====================================================================
Pixel-perfect recreation of the web ID card shown at
  /personnel/<id>/
using the same CSS values found in personnel_profile_detail.html.

Card format : Portrait CR80 @ 300 DPI  →  638 × 1013 px
Three files  : <id>_front.png  |  <id>_back.png  |  <id>.png (both side-by-side)
Output dir   : core/media/personnel_id_cards/

CSS reference  (personnel_profile_detail.html)
──────────────────────────────────────────────
  .id-card-face        220 × 349 px  border-radius 14px
  .id-card-top         gradient 135deg  #1e40af → #2563eb
  .id-card-logo        0.65rem  wt-800  ls-0.12em  rgba(255,255,255,0.75)
  .profile-photo       100 × 110 px  border-radius 8px  border 3px white
  .id-card-body        white  padding 0.75rem 1rem
  .profile-name        0.9rem  wt-800  uppercase  #111827
  .badge-pill          0.7rem  wt-700  uppercase  border-radius 999px
  .id-card-footer      52 px  bg #f9fafb  border-top #f3f4f6
  .id-card-id-label    0.62rem  wt-700  uppercase  ls-0.08em  #9ca3af
  .id-card-id-value    monospace  0.78rem  wt-700  #374151  ls-0.04em
"""

import os
import logging
from PIL import Image, ImageDraw, ImageOps, ImageFilter

import qrcode
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── Card pixel dimensions (portrait CR80 @ 300 DPI) ──────────────────────
CARD_W  = 638
CARD_H  = 1013

# Scale factor from CSS design (220 × 349) to PNG
_SX = CARD_W / 220   # ≈ 2.9
_SY = CARD_H / 349   # ≈ 2.9

def _px(css_px: float) -> int:
    """Scale a CSS pixel value to PNG space (uses width axis)."""
    return max(1, round(css_px * _SX))

# ─── Section heights ───────────────────────────────────────────────────────
FOOTER_H = round(52 * _SY)          # ~151 px
TOP_H    = round(178 * _SY)         # ~523 px  (logo + photo + paddings)
BODY_H   = CARD_H - TOP_H - FOOTER_H

# ─── Colour palette (straight from CSS) ───────────────────────────────────
GRAD_START   = (30,  64, 175)   # #1e40af
GRAD_END     = (37,  99, 235)   # #2563eb
WHITE        = (255, 255, 255)
CARD_BG      = (255, 255, 255)
BODY_BG      = (255, 255, 255)
FOOTER_BG    = (249, 250, 251)   # #f9fafb
FOOTER_DIV   = (243, 244, 246)   # #f3f4f6
NAME_COLOR   = (17,  24,  39)    # #111827
LOGO_COLOR   = (255, 255, 255, 192)  # rgba(255,255,255,0.75)
FOOTER_LABEL = (156, 163, 175)   # #9ca3af
FOOTER_VAL   = (55,  65,  81)    # #374151

# Badge colours
BADGE = {
    'OFFICER':            {'bg': (219, 234, 254), 'fg': (30, 64, 175)},   # #dbeafe / #1e40af
    'ENLISTED PERSONNEL': {'bg': (220, 252, 231), 'fg': (22, 101, 52)},   # #dcfce7 / #166534
    'SUPERUSER':          {'bg': (254, 243, 199), 'fg': (146, 64, 14)},   # #fef3c7 / #92400e
}
BADGE_DEFAULT = BADGE['ENLISTED PERSONNEL']

# ─── Font loader ───────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False, mono: bool = False):
    key = (size, bold, mono)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    from PIL import ImageFont
    if mono:
        # Monospace — matches CSS font-family:monospace (Courier New)
        candidates = [
            r"C:\Windows\Fonts\courbd.ttf" if bold else r"C:\Windows\Fonts\cour.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    else:
        candidates = (
            [r"C:\Windows\Fonts\arialbd.ttf",
             r"C:\Windows\Fonts\calibrib.ttf",
             r"C:\Windows\Fonts\segoeuib.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if bold else
            [r"C:\Windows\Fonts\arial.ttf",
             r"C:\Windows\Fonts\calibri.ttf",
             r"C:\Windows\Fonts\segoeui.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
    font = None
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                break
            except (IOError, OSError):
                continue
    _FONT_CACHE[key] = font or ImageFont.load_default()
    return _FONT_CACHE[key]


# ─── Helpers ───────────────────────────────────────────────────────────────

def _gradient_rect(img: Image.Image, x0: int, y0: int, x1: int, y1: int,
                   c_start: tuple, c_end: tuple, angle: int = 135):
    """Fill a rect with a diagonal linear gradient (135 °)."""
    draw = ImageDraw.Draw(img)
    w = x1 - x0
    h = y1 - y0
    # 135° line: combine x and y progress equally
    for y in range(h):
        for x in range(w):
            t = ((x / max(w - 1, 1)) + (y / max(h - 1, 1))) / 2
            r = round(c_start[0] + (c_end[0] - c_start[0]) * t)
            g = round(c_start[1] + (c_end[1] - c_start[1]) * t)
            b = round(c_start[2] + (c_end[2] - c_start[2]) * t)
            draw.point((x0 + x, y0 + y), fill=(r, g, b))


def _text_w(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _text_h(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _centred_text(draw, cx: int, y: int, text: str, font, fill, letter_spacing: int = 0):
    """Draw text horizontally centred at cx.  Optional per-character spacing."""
    if letter_spacing == 0:
        w = _text_w(draw, text, font)
        draw.text((cx - w // 2, y), text, font=font, fill=fill)
    else:
        chars = list(text)
        widths = [_text_w(draw, c, font) + letter_spacing for c in chars]
        total  = sum(widths) - letter_spacing
        x = cx - total // 2
        for c, cw in zip(chars, widths):
            draw.text((x, y), c, font=font, fill=fill)
            x += cw


def _wrap_text(draw, text: str, font, max_w: int) -> list[str]:
    """Word-wrap text to fit within max_w pixels."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if _text_w(draw, test, font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _rounded_rect(draw, xy, radius, fill, outline=None, outline_width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill,
                            outline=outline, width=outline_width)


def _add_rounded_corners(img: Image.Image, radius: int) -> Image.Image:
    """Return a copy with transparent rounded corners (PNG-safe)."""
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([(0, 0), (img.width - 1, img.height - 1)],
                             radius=radius, fill=255)
    img.putalpha(mask)
    return img


# ─── FRONT card ────────────────────────────────────────────────────────────

def _build_front(personnel) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (*WHITE, 255))
    draw = ImageDraw.Draw(card)

    # ── Top gradient section ──────────────────────────────────────────
    _gradient_rect(card, 0, 0, CARD_W, TOP_H, GRAD_START, GRAD_END)

    # Logo — .id-card-logo: font-size 0.65rem=10.4px→30px, wt-800, ls 0.12em=1.25px→4px
    #         color rgba(255,255,255,0.75)=192 alpha
    logo_font = _font(30, bold=True)
    logo_text = "ARMORY CARD"
    logo_y    = _px(11)   # padding-top: 0.7rem = 11.2px CSS
    _centred_text(draw, CARD_W // 2, logo_y, logo_text,
                  logo_font, (*LOGO_COLOR[:3], 192), letter_spacing=4)

    # Profile photo
    photo_w  = _px(100)
    photo_h  = _px(110)
    photo_bw = _px(3)      # border width
    photo_radius = _px(8)

    try:
        if personnel.picture and os.path.exists(personnel.picture.path):
            photo = Image.open(personnel.picture.path).convert("RGBA")
            photo = ImageOps.fit(photo, (photo_w, photo_h), method=Image.LANCZOS)
        else:
            raise FileNotFoundError
    except Exception:
        # Placeholder silhouette on semi-transparent white background
        photo = Image.new("RGBA", (photo_w, photo_h), (255, 255, 255, 38))  # rgba(255,255,255,0.15)
        ph_draw = ImageDraw.Draw(photo)
        cx = photo_w // 2
        # Head
        head_r = photo_w // 5
        ph_draw.ellipse([cx - head_r, photo_h // 8,
                          cx + head_r, photo_h // 8 + head_r * 2],
                         fill=(255, 255, 255, 178))
        # Body
        ph_draw.ellipse([cx - photo_w // 3, photo_h // 2,
                          cx + photo_w // 3, photo_h + photo_w // 4],
                         fill=(255, 255, 255, 178))

    # White border around photo (draw on card as a rounded rect then paste photo)
    logo_bb   = draw.textbbox((0, 0), logo_text, font=logo_font)
    logo_h    = logo_bb[3] - logo_bb[1]
    gap_after_logo = _px(8)    # 0.5rem gap

    photo_x  = (CARD_W - photo_w) // 2
    photo_y  = logo_y + logo_h + gap_after_logo   # one flex gap (0.5rem)

    # White rounded border rect
    bx0, by0 = photo_x - photo_bw, photo_y - photo_bw
    bx1, by1 = photo_x + photo_w + photo_bw, photo_y + photo_h + photo_bw
    _rounded_rect(draw, [bx0, by0, bx1, by1],
                  radius=photo_radius + photo_bw,
                  fill=(255, 255, 255, 230))

    # Paste photo with rounded corners onto card
    photo_rounded = _add_rounded_corners(photo, photo_radius)
    card.alpha_composite(photo_rounded, (photo_x, photo_y))

    # Recalculate TOP_H from content if photo bottom exceeds estimate
    actual_top_h = by1 + _px(8)   # 0.5rem bottom padding in id-card-top

    draw = ImageDraw.Draw(card)   # refresh draw after alpha_composite

    # ── White body section ────────────────────────────────────────────
    body_y0 = actual_top_h
    body_y1 = CARD_H - FOOTER_H
    draw.rectangle([0, body_y0, CARD_W, body_y1], fill=(*BODY_BG, 255))

    # Name: "RANK FIRSTNAME MI SURNAME"  (matches {{ personnel.rank }} {{ personnel.get_full_name }})
    # get_full_name() returns "FIRSTNAME MI SURNAME" — no period after MI
    full_name = f"{(personnel.rank or '').upper()} {personnel.get_full_name().upper()}".strip()

    # CSS: profile-name  font-size 0.9rem → _px(14.4)≈42px, line-height 1.25
    # CSS: id-card-body  padding 0.75rem top, gap 0.3rem between items
    name_font  = _font(42, bold=True)
    name_max_w = CARD_W - _px(16)   # 1rem total side padding
    name_lines = _wrap_text(draw, full_name, name_font, name_max_w)
    if len(name_lines) > 3:
        name_font  = _font(34, bold=True)
        name_lines = _wrap_text(draw, full_name, name_font, name_max_w)

    BODY_GAP = _px(5)             # 0.3rem flex gap between children  (≈14px)
    LINE_H   = round(_text_h(draw, "A", name_font) * 1.25)  # line-height 1.25
    pad_y    = _px(12)            # 0.75rem top padding in id-card-body
    cur_y    = body_y0 + pad_y

    for i, line in enumerate(name_lines):
        # .profile-name letter-spacing 0.03em = 0.43px CSS → 1px PNG
        _centred_text(draw, CARD_W // 2, cur_y, line, name_font, NAME_COLOR, letter_spacing=1)
        if i < len(name_lines) - 1:
            cur_y += LINE_H           # tight line-height within same <p>
        else:
            cur_y += LINE_H + BODY_GAP   # flex gap before next sibling

    # Serial + PAF  — .profile-role: same font + letter-spacing as profile-name
    serial_font = name_font
    serial_str  = f"{personnel.serial} PAF"
    _centred_text(draw, CARD_W // 2, cur_y, serial_str, serial_font, NAME_COLOR, letter_spacing=1)
    cur_y += LINE_H + BODY_GAP     # flex gap before badges

    # Classification badge pill
    # CSS: padding 0.18rem 0.65rem  → bpad_y=_px(2.9)≈8px, bpad_x=_px(10.4)≈30px
    # CSS: font-size 0.7rem → _px(11.2)≈32px, font-weight 700
    classif = (personnel.classification or "ENLISTED PERSONNEL").upper()
    badge_colors = BADGE.get(classif, BADGE_DEFAULT)
    badge_label  = classif.replace("ENLISTED PERSONNEL", "ENLISTED")

    badge_font = _font(32, bold=True)
    bpad_x     = _px(10)    # 0.65rem = 10.4px CSS
    bpad_y     = _px(3)     # 0.18rem = 2.88px CSS
    bw = _text_w(draw, badge_label, badge_font) + bpad_x * 2
    bh = _text_h(draw, badge_label, badge_font) + bpad_y * 2
    bx = (CARD_W - bw) // 2
    by = cur_y
    _rounded_rect(draw, [bx, by, bx + bw, by + bh],
                  radius=bh // 2, fill=badge_colors['bg'])
    # .badge-pill letter-spacing 0.04em = 0.45px CSS → 1px PNG
    _centred_text(draw, CARD_W // 2, by + bpad_y, badge_label,
                  badge_font, badge_colors['fg'], letter_spacing=1)

    # ── Footer section ────────────────────────────────────────────────
    footer_y0 = CARD_H - FOOTER_H
    draw.rectangle([0, footer_y0, CARD_W, CARD_H], fill=FOOTER_BG)
    draw.line([(0, footer_y0), (CARD_W, footer_y0)], fill=FOOTER_DIV, width=2)

    lbl_font = _font(29, bold=True)
    val_font = _font(36, bold=True, mono=True)   # .id-card-id-value: font-family monospace

    # Centre both label+value vertically within footer
    lbl_h = _text_h(draw, "PERSONNEL ID", lbl_font)
    val_h = _text_h(draw, personnel.id, val_font)
    gap   = _px(2)     # gap: 0.1rem = 1.6px CSS → ~5px PNG
    total_text_h = lbl_h + gap + val_h
    lbl_y = footer_y0 + (FOOTER_H - total_text_h) // 2

    # .id-card-id-label: letter-spacing 0.08em = 0.79px CSS → 2px PNG
    _centred_text(draw, CARD_W // 2, lbl_y, "PERSONNEL ID", lbl_font, FOOTER_LABEL, letter_spacing=2)
    # .id-card-id-value: letter-spacing 0.04em = 0.5px CSS → 1px PNG
    _centred_text(draw, CARD_W // 2, lbl_y + lbl_h + gap, personnel.id, val_font, FOOTER_VAL, letter_spacing=1)

    # Apply card-level rounded corners (14px → scaled) + outer border: 1px solid #e5e7eb
    card = _add_rounded_corners(card.convert("RGBA"), _px(14))
    # Draw border outline on top of rounded card
    border_draw = ImageDraw.Draw(card)
    border_draw.rounded_rectangle(
        [0, 0, CARD_W - 1, CARD_H - 1],
        radius=_px(14),
        outline=(229, 231, 235),   # #e5e7eb
        width=max(1, _px(1)),
    )

    # Return as RGB with white background
    bg = Image.new("RGB", card.size, WHITE)
    bg.paste(card, mask=card.split()[3])
    return bg


# ─── BACK card ─────────────────────────────────────────────────────────────

def _build_back(personnel) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (*WHITE, 255))
    draw = ImageDraw.Draw(card)

    # ── Top gradient: small strip — logo only (no photo on back) ──────
    logo_font = _font(34, bold=True)
    logo_text = "ARMORY CARD"
    logo_y    = _px(11)
    # Compute header height from logo text + top/bottom padding
    _tmp_draw   = ImageDraw.Draw(card)
    logo_bb_h   = _tmp_draw.textbbox((0, 0), logo_text, font=logo_font)
    logo_txt_h  = logo_bb_h[3] - logo_bb_h[1]
    back_top_h  = logo_y + logo_txt_h + _px(11)   # equal top+bottom padding

    _gradient_rect(card, 0, 0, CARD_W, back_top_h, GRAD_START, GRAD_END)
    draw = ImageDraw.Draw(card)
    _centred_text(draw, CARD_W // 2, logo_y, logo_text,
                  logo_font, (*LOGO_COLOR[:3], 192), letter_spacing=6)

    # ── White body ────────────────────────────────────────────────────
    body_y0 = back_top_h
    body_y1 = CARD_H - FOOTER_H
    draw.rectangle([0, body_y0, CARD_W, body_y1], fill=(*BODY_BG, 255))

    # ── QR code — match exact style from utils/qr_generator.py:
    #   fill_color="#888888" (gray) on back_color="black"
    #   Try to load the stored QR image first; fall back to fresh generation.
    available_h = body_y1 - body_y0
    qr_size     = min(available_h - _px(28), CARD_W - _px(36))
    qr_size     = qr_size - (qr_size % 2)

    qr_img = None
    try:
        from qr_manager.models import QRCodeImage
        qr_obj = QRCodeImage.objects.filter(
            qr_type=QRCodeImage.TYPE_PERSONNEL,
            reference_id=personnel.id
        ).first()
        if qr_obj and qr_obj.qr_image:
            qr_img = Image.open(qr_obj.qr_image.path).convert("RGBA")
    except Exception:
        pass

    if qr_img is None:
        # Replicate qr_generator.py style exactly
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
            border=2,
        )
        qr.add_data(str(personnel.id))
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#888888", back_color="black").convert("RGBA")
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    # Rounded corners on QR: border-radius 8px → _px(8)
    qr_rounded = _add_rounded_corners(qr_img, _px(8))

    # Position: centre QR in body; back body padding is 1rem each side
    body_y0_back = back_top_h
    body_y1_back = CARD_H - FOOTER_H
    qr_x = (CARD_W - qr_size) // 2
    qr_y = body_y0_back + (body_y1_back - body_y0_back - qr_size) // 2

    # Draw thin border around QR: border 1px solid #e5e7eb (tight, no extra white frame)
    qr_border_w = max(1, _px(1))
    draw.rounded_rectangle(
        [qr_x - qr_border_w, qr_y - qr_border_w,
         qr_x + qr_size + qr_border_w, qr_y + qr_size + qr_border_w],
        radius=_px(8) + qr_border_w,
        outline=(229, 231, 235),   # #e5e7eb
        width=qr_border_w,
    )

    draw = ImageDraw.Draw(card)
    card.alpha_composite(qr_rounded, (qr_x, qr_y))

    draw = ImageDraw.Draw(card)

    # ── Footer (same as front) ────────────────────────────────────────
    footer_y0 = CARD_H - FOOTER_H
    draw.rectangle([0, footer_y0, CARD_W, CARD_H], fill=FOOTER_BG)
    draw.line([(0, footer_y0), (CARD_W, footer_y0)], fill=FOOTER_DIV, width=2)

    lbl_font = _font(29, bold=True)
    val_font = _font(36, bold=True, mono=True)   # monospace — same as front footer
    lbl_h    = _text_h(draw, "PERSONNEL ID", lbl_font)
    val_h    = _text_h(draw, personnel.id, val_font)
    gap      = _px(2)
    total_text_h = lbl_h + gap + val_h
    lbl_y    = footer_y0 + (FOOTER_H - total_text_h) // 2

    _centred_text(draw, CARD_W // 2, lbl_y, "PERSONNEL ID", lbl_font, FOOTER_LABEL, letter_spacing=2)
    _centred_text(draw, CARD_W // 2, lbl_y + lbl_h + gap, personnel.id, val_font, FOOTER_VAL, letter_spacing=1)

    # Rounded corners + outer border
    card = _add_rounded_corners(card.convert("RGBA"), _px(14))
    border_draw = ImageDraw.Draw(card)
    border_draw.rounded_rectangle(
        [0, 0, CARD_W - 1, CARD_H - 1],
        radius=_px(14),
        outline=(229, 231, 235),
        width=max(1, _px(1)),
    )
    bg   = Image.new("RGB", card.size, WHITE)
    bg.paste(card, mask=card.split()[3])
    return bg


# ─── Public API ────────────────────────────────────────────────────────────

def generate_personnel_id_card(personnel) -> dict:
    """
    Generate front + back ID card PNGs for *personnel* and save them to
    ``MEDIA_ROOT/personnel_id_cards/``.

    Returns:
        {
          'combined': 'personnel_id_cards/<id>.png',   (both sides)
          'front':    'personnel_id_cards/<id>_front.png',
          'back':     'personnel_id_cards/<id>_back.png',
        }
    """
    out_dir = os.path.join(settings.MEDIA_ROOT, "personnel_id_cards")
    os.makedirs(out_dir, exist_ok=True)

    pid = personnel.id  # e.g. "PO-154068180226"

    front = _build_front(personnel)
    back  = _build_back(personnel)

    front_path    = os.path.join(out_dir, f"{pid}_front.png")
    back_path     = os.path.join(out_dir, f"{pid}_back.png")
    combined_path = os.path.join(out_dir, f"{pid}.png")

    front.save(front_path,    "PNG", dpi=(300, 300), optimize=False)
    back.save(back_path,      "PNG", dpi=(300, 300), optimize=False)

    # Combined: both cards side-by-side with a small gap
    GAP  = 30
    BG   = (226, 232, 240)   # #e2e8f0 light blue-gray
    comb = Image.new("RGB", (CARD_W * 2 + GAP, CARD_H), BG)
    comb.paste(front, (0, 0))
    comb.paste(back,  (CARD_W + GAP, 0))
    comb.save(combined_path, "PNG", dpi=(300, 300), optimize=False)

    logger.info("ID card generated → %s", combined_path)
    return {
        "combined": f"personnel_id_cards/{pid}.png",
        "front":    f"personnel_id_cards/{pid}_front.png",
        "back":     f"personnel_id_cards/{pid}_back.png",
    }
