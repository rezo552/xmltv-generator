"""Generate simple channel logos (PNG) for the channels in mdb_lists.cfg.

Each logo is a rounded tile with a gradient, a symbol (picked from keywords in
the display name, otherwise the channel initials) and the channel name.

Usage: python tools/make_logos.py [mdb_lists.cfg] [output_dir]
Requires Pillow and the DejaVu fonts (fonts-dejavu-core on Debian).
Existing files are overwritten; logos/<channel_id>.png is what app.py serves.
"""
import csv
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SIZE = 512
SCALE = 4  # draw supersampled, then downscale for smooth edges
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_SYMBOLS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

# (top colour, bottom colour) pairs, used in order
PALETTE = [
    ('#3a7bd5', '#1c3f78'), ('#8e44ad', '#4a1f63'), ('#16a085', '#0b5345'),
    ('#e67e22', '#8a4510'), ('#2c3e50', '#0f1720'), ('#c0392b', '#5e1a13'),
    ('#f1c40f', '#9a7b06'), ('#d35400', '#6e2c00'), ('#6c5ce7', '#2d2580'),
    ('#00b894', '#00624e'), ('#fd79a8', '#a33a62'), ('#636e72', '#2d3436'),
    ('#0984e3', '#043f6e'), ('#b33771', '#5a1b38'),
]

# keyword in the display name (lower case) -> candidate symbols, first one the font has wins
SYMBOLS = [
    ('weekly', '★'),                # star
    ('top', '★'),
    ('action', '⚡'),                # lightning
    ('mindfuck', '∞'),              # infinity
    ('fantasy', '✦'),               # four pointed star
    ('sci-fi', '✦'),
    ('comedy', '☺'),                # smiley
    ('thriller', '⌛⌖⚠'),  # hourglass, crosshair, warning sign
    ('crime', '⚖'),                 # scales
    ('drama', '♥'),                 # heart
]


def read_channels(cfg_path):
    channels = []
    with open(cfg_path, encoding='utf-8') as f:
        for row in csv.reader(f):
            if not row or row[0].startswith('#') or len(row) < 2:
                continue
            username_list, display_name = row[0].strip(), row[1].strip()
            if '/' in username_list and display_name:
                channels.append((username_list.split('/', 1)[1], display_name))
    return channels


def has_glyph(font, char):
    # Compare with the glyph of an unassigned code point (the "missing" box)
    def render(text):
        image = Image.new('L', (font.size * 2, font.size * 2), 0)
        ImageDraw.Draw(image).text((0, 0), text, font=font, fill=255)
        return image
    return ImageChops.difference(render(char), render('\U000f0000')).getbbox() is not None


def pick_symbol(display_name, symbol_font):
    name = display_name.lower()
    for keyword, candidates in SYMBOLS:
        if keyword not in name:
            continue
        for symbol in candidates:
            if has_glyph(symbol_font, symbol):
                return symbol, symbol_font
    words = [w for w in display_name.replace('+', ' +').split() if w[0].isalnum() or w == '+']
    initials = ''.join(w[0] for w in words[:2]).upper() or display_name[:2].upper()
    return initials, None


def fit_font(path, text, max_width, start_size):
    size = start_size
    while size > 10:
        font = ImageFont.truetype(path, size)
        left, _, right, _ = font.getbbox(text)
        if right - left <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(path, size)


def fit_symbol_font(path, text, max_width, max_height):
    # Scale so the glyph itself (not the font's line box) fills the target area
    probe = 200
    left, top, right, bottom = ImageFont.truetype(path, probe).getbbox(text)
    ratio = min(max_width / max(right - left, 1), max_height / max(bottom - top, 1))
    return ImageFont.truetype(path, max(int(probe * ratio), 10))


def gradient(width, height, top, bottom):
    top_rgb = Image.new('RGB', (1, 1), top).getpixel((0, 0))
    bottom_rgb = Image.new('RGB', (1, 1), bottom).getpixel((0, 0))
    column = Image.new('RGB', (1, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top_rgb, bottom_rgb)))
    return column.resize((width, height))


def draw_centered(draw, box, text, font, fill):
    left, top, right, bottom = font.getbbox(text)
    x = box[0] + (box[2] - box[0] - (right - left)) / 2 - left
    y = box[1] + (box[3] - box[1] - (bottom - top)) / 2 - top
    draw.text((x, y), text, font=font, fill=fill)


def make_logo(display_name, colours):
    s = SIZE * SCALE
    margin = 16 * SCALE
    radius = 96 * SCALE
    tile = gradient(s, s, *colours).convert('RGBA')
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((margin, margin, s - margin, s - margin), radius, fill=255)

    symbol_font = ImageFont.truetype(FONT_SYMBOLS, 300 * SCALE)
    symbol, font = pick_symbol(display_name, symbol_font)
    if font is None:
        font = fit_font(FONT_BOLD, symbol, s - 8 * margin, 230 * SCALE)
    else:
        font = fit_symbol_font(FONT_SYMBOLS, symbol, int(s * 0.62), int(s * 0.46))

    # symbol with a soft shadow in the upper part of the tile
    symbol_box = (margin, margin + 20 * SCALE, s - margin, int(s * 0.68))
    shadow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw_centered(ImageDraw.Draw(shadow), (symbol_box[0], symbol_box[1] + 8 * SCALE, symbol_box[2], symbol_box[3] + 8 * SCALE),
                  symbol, font, (0, 0, 0, 110))
    tile = Image.alpha_composite(tile, shadow.filter(ImageFilter.GaussianBlur(10 * SCALE)))
    draw = ImageDraw.Draw(tile)
    draw_centered(draw, symbol_box, symbol, font, (255, 255, 255, 255))

    # channel name on a darker band at the bottom
    band_top = int(s * 0.72)
    band = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle((0, band_top, s, s), fill=(0, 0, 0, 90))
    tile = Image.alpha_composite(tile, band)
    draw = ImageDraw.Draw(tile)
    name_font = fit_font(FONT_BOLD, display_name, s - 4 * margin, 64 * SCALE)
    draw_centered(draw, (margin, band_top, s - margin, s - margin), display_name, name_font, (255, 255, 255, 255))

    logo = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    logo.paste(tile, (0, 0), mask)
    return logo.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else 'mdb_lists.cfg'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'logos'
    os.makedirs(out_dir, exist_ok=True)
    for index, (channel_id, display_name) in enumerate(read_channels(cfg_path)):
        path = os.path.join(out_dir, f'{channel_id}.png')
        make_logo(display_name, PALETTE[index % len(PALETTE)]).save(path, optimize=True)
        print(f'{path}  ({display_name})')


if __name__ == '__main__':
    main()
