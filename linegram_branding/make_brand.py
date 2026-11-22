#!/usr/bin/env python3
"""Regenerate every LineGram logo asset inside the Android project.

Run from anywhere:   python3 linegram_branding/make_brand.py
Needs: Python 3 with Pillow and fontTools, plus the `rsvg-convert` tool (librsvg).

What it writes (always at the pixel size and file format of the file it replaces):
  * launcher icons: adaptive foregrounds, legacy PNGs, all six icon variants
  * the notification icon, the account icon, the intro logo, two in-app logo discs
  * vector drawables: themed (monochrome) icon, the "LineGram" wordmark,
    the Android 12 splash animation, the default icon background colours
  * the logo drawn in the middle of QR codes, and the two animated logos (Lottie)

Change BRAND_* below (or the shape in lg_mark.py) and run again to restyle the app.
"""
import base64
import io
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lg_mark as mark  # noqa: E402

RES = os.path.join(ROOT, 'TMessagesProj', 'src', 'main', 'res')
SA_RES = os.path.join(ROOT, 'TMessagesProj_AppStandalone', 'src', 'main', 'res')

# ---- brand colours -----------------------------------------------------------
BRAND_TOP = '#FF9A3D'      # top of the icon gradient
BRAND_BOTTOM = '#F2542D'   # bottom of the icon gradient
BRAND_FLAT = '#F96B33'     # single-colour uses: splash circle, intro sphere, QR logo
WORDMARK_TEXT = 'LineGram'
# DM Sans (SIL Open Font License) is only needed to redraw the wordmark.
WORDMARK_FONT = '/usr/share/fonts/truetype/google-fonts/ofl/dmsans/DMSans[opsz,wght].ttf'

DENSITIES = {'mdpi': 1.0, 'hdpi': 1.5, 'xhdpi': 2.0, 'xxhdpi': 3.0, 'xxxhdpi': 4.0}
written = []


# ---- helpers -----------------------------------------------------------------
def render(svg, w, h):
    """Rasterise an SVG string to an RGBA image of exactly w x h pixels."""
    out = subprocess.run(['rsvg-convert', '-w', str(w), '-h', str(h), '-f', 'png'],
                         input=svg.encode('utf-8'), stdout=subprocess.PIPE, check=True).stdout
    img = Image.open(io.BytesIO(out)).convert('RGBA')
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    return img


def replace_image(path, svg):
    """Overwrite an existing bitmap with the SVG, keeping its pixel size and format."""
    if not os.path.exists(path):
        return False
    with Image.open(path) as old:
        w, h = old.size
    img = render(svg, w, h)
    if path.lower().endswith('.webp'):
        img.save(path, 'WEBP', lossless=True, quality=100, method=6)
    else:
        img.save(path, 'PNG', optimize=True)
    written.append(os.path.relpath(path, ROOT))
    return True


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    written.append(os.path.relpath(path, ROOT))


def data_uri(path):
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')


def brand_gradient(gid='bg', x=0, y=0, size=108):
    """Vertical brand gradient over a square (Android angle=90: bottom -> top)."""
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{y + size}" x2="0" y2="{y}">'
            f'<stop offset="0" stop-color="{BRAND_BOTTOM}"/><stop offset="1" stop-color="{BRAND_TOP}"/></linearGradient>')


def variant_background(variant):
    """SVG <defs> + drawing of an icon variant's 108x108 dp adaptive background."""
    if variant == 'default':
        return brand_gradient(), '<rect width="108" height="108" fill="url(#bg)"/>'
    if variant == '2':   # "Nox": star field bitmap shipped with the app
        uri = data_uri(os.path.join(RES, 'mipmap-xxxhdpi', 'icon_2_background_sa.png'))
        return '', f'<image x="0" y="0" width="108" height="108" href="{uri}" xlink:href="{uri}"/>'
    if variant == '3':   # "Premium": angle -45 linear + two radial glows
        defs = ('<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="108" y2="108">'
                '<stop offset="0" stop-color="#FC5DDC"/><stop offset="1" stop-color="#9484FF"/></linearGradient>'
                '<radialGradient id="bg2" gradientUnits="userSpaceOnUse" cx="108" cy="0" r="70.2">'
                '<stop offset="0" stop-color="#F4817F" stop-opacity="1"/><stop offset="1" stop-color="#F4817F" stop-opacity="0"/></radialGradient>'
                '<radialGradient id="bg3" gradientUnits="userSpaceOnUse" cx="0" cy="108" r="86.4">'
                '<stop offset="0" stop-color="#5381FE" stop-opacity="1"/><stop offset="0.5" stop-color="#5381FE" stop-opacity="0.573"/>'
                '<stop offset="1" stop-color="#5381FE" stop-opacity="0"/></radialGradient>')
        return defs, ('<rect width="108" height="108" fill="url(#bg)"/><rect width="108" height="108" fill="url(#bg2)"/>'
                      '<rect width="108" height="108" fill="url(#bg3)"/>')
    if variant in ('4', '5'):   # angle 45: bottom-left -> top-right, three stops
        stops = {'4': ('#137BE5', '#02A3CC', '#00DC6B'), '5': ('#9651FF', '#3A8FFF', '#49F9FA')}[variant]
        defs = ('<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="0" y1="108" x2="108" y2="0">'
                f'<stop offset="0" stop-color="{stops[0]}"/><stop offset="0.5" stop-color="{stops[1]}"/>'
                f'<stop offset="1" stop-color="{stops[2]}"/></linearGradient>')
        return defs, '<rect width="108" height="108" fill="url(#bg)"/>'
    if variant in EXTRA_ICONS:   # LineGram's own colours: plain vertical gradient
        bottom, top = EXTRA_ICONS[variant][1], EXTRA_ICONS[variant][2]
        defs = ('<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="0" y1="108" x2="0" y2="0">'
                f'<stop offset="0" stop-color="{bottom}"/><stop offset="1" stop-color="{top}"/></linearGradient>')
        return defs, '<rect width="108" height="108" fill="url(#bg)"/>'
    if variant == '6':   # "Vintage": plain vertical blue
        defs = ('<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="0" y1="108" x2="0" y2="0">'
                '<stop offset="0" stop-color="#1D93D2"/><stop offset="1" stop-color="#37AFE3"/></linearGradient>')
        return defs, '<rect width="108" height="108" fill="url(#bg)"/>'
    raise ValueError(variant)


SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}">'

# ---- extra LineGram launcher icons (chosen in Settings > LineGram Settings) ----
# number -> (manifest alias key, gradient bottom, gradient top)
EXTRA_ICONS = {
    '7': ('NightIcon', '#121216', '#3A3A44'),
    '8': ('EmeraldIcon', '#0E8F73', '#35D98A'),
    '9': ('RubyIcon', '#B5122E', '#FF5C6C'),
    '10': ('GoldIcon', '#D98A06', '#FFCF4D'),
}

ADAPTIVE_ICON = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/{background}" />
    <foreground android:drawable="@mipmap/{foreground}" />
    <monochrome android:drawable="@drawable/icon_plane" />
</adaptive-icon>
"""


def make_extra_icons():
    """Creates every file an extra icon needs (the six built-in ones already exist)."""
    sizes = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    for n, (_key, bottom, top) in EXTRA_ICONS.items():
        write_text(os.path.join(RES, 'drawable', f'icon_{n}_background_sa.xml'),
                   '<?xml version="1.0" encoding="utf-8"?>\n'
                   '<shape xmlns:android="http://schemas.android.com/apk/res/android">\n'
                   '    <gradient\n'
                   '        android:type="linear"\n'
                   '        android:angle="90"\n'
                   f'        android:startColor="{bottom}"\n'
                   f'        android:endColor="{top}" />\n'
                   '</shape>\n')
        for suffix, clip in (('', 'icon_background_clip'), ('_round', 'icon_background_clip_round')):
            write_text(os.path.join(RES, 'drawable', f'icon_{n}_background{suffix}.xml'),
                       '<?xml version="1.0" encoding="utf-8"?>\n'
                       '<layer-list xmlns:android="http://schemas.android.com/apk/res/android">\n'
                       f'    <item android:drawable="@drawable/icon_{n}_background_sa" />\n'
                       f'    <item android:drawable="@mipmap/{clip}" />\n'
                       '</layer-list>\n')
            write_text(os.path.join(RES, 'mipmap-anydpi-v26', f'icon_{n}_launcher{suffix}.xml'),
                       ADAPTIVE_ICON.format(background=f'icon_{n}_background{suffix}', foreground=f'icon_foreground{suffix}'))
        ring = ring_icon_svg(n)
        for d, px in sizes.items():
            for suffix in ('', '_round'):
                path = os.path.join(RES, f'mipmap-{d}', f'icon_{n}_launcher{suffix}.png')
                render(ring, px, px).save(path, 'PNG', optimize=True)
                written.append(os.path.relpath(path, ROOT))


# ---- 1. adaptive icon foregrounds (108 x 108 dp, white mark) --------------------
def foreground_svg(height_dp):
    return (SVG_HEAD.format(w=108, h=108) +
            f'<path d="{mark.placed(height_dp, 54, 54)}" fill="#FFFFFF"/></svg>')


def make_foregrounds():
    heights = {'': 33.0, '_round': 36.0, '_sa': 37.0}   # ring hole is 58 dp / 64 dp / none
    for d in DENSITIES:
        for prefix in ('icon_foreground', 'icon_3_foreground', 'icon_5_foreground', 'icon_6_foreground'):
            for suffix, hdp in heights.items():
                replace_image(os.path.join(RES, f'mipmap-{d}', f'{prefix}{suffix}.png'), foreground_svg(hdp))


# ---- 2. legacy launcher bitmaps (48 dp): white ring + background + mark --------
def ring_icon_svg(variant):
    """192 x 192 design: white disc r=92, coloured disc r=82 (the 58 dp ring hole)."""
    s = 164.0 / 58.0                       # px per dp so that the 58 dp hole is 164 px wide
    off = 96.0 - 54.0 * s                  # where the 108 dp canvas starts
    defs, bg = variant_background(variant)
    return (SVG_HEAD.format(w=192, h=192) +
            '<defs><clipPath id="hole"><circle cx="96" cy="95.5" r="82"/></clipPath>'
            '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2"/></filter>'
            f'{defs}</defs>'
            '<circle cx="96" cy="97.5" r="90" fill="#000000" opacity="0.22" filter="url(#sh)"/>'
            '<circle cx="96" cy="95.5" r="92" fill="#FFFFFF"/>'
            f'<g clip-path="url(#hole)"><g transform="translate({off:.4f},{off - 0.5:.4f}) scale({s:.5f})">{bg}</g></g>'
            f'<path d="{mark.placed(33.0 * s, 96, 95.5)}" fill="#FFFFFF"/></svg>')


def plain_icon_svg(variant):
    """192 x 192 design without ring (standalone app): coloured disc r=88 with soft shadow."""
    s = 176.0 / 72.0                       # the launcher shows a 72 dp circle of the 108 dp canvas
    off = 96.0 - 54.0 * s
    defs, bg = variant_background(variant)
    return (SVG_HEAD.format(w=192, h=192) +
            '<defs><clipPath id="disc"><circle cx="96" cy="95.5" r="88"/></clipPath>'
            '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.4"/></filter>'
            f'{defs}</defs>'
            '<circle cx="96" cy="98" r="87" fill="#000000" opacity="0.28" filter="url(#sh)"/>'
            f'<g clip-path="url(#disc)"><g transform="translate({off:.4f},{off - 0.5:.4f}) scale({s:.5f})">{bg}</g></g>'
            f'<path d="{mark.placed(37.0 * s, 96, 95.5)}" fill="#FFFFFF"/></svg>')


def make_legacy_icons():
    names = {'default': 'ic_launcher', '2': 'icon_2_launcher', '3': 'icon_3_launcher',
             '4': 'icon_4_launcher', '5': 'icon_5_launcher', '6': 'icon_6_launcher'}
    for variant, name in names.items():
        ring, plain = ring_icon_svg(variant), plain_icon_svg(variant)
        for d in DENSITIES:
            replace_image(os.path.join(RES, f'mipmap-{d}', f'{name}.png'), ring)
            replace_image(os.path.join(RES, f'mipmap-{d}', f'{name}_round.png'), ring)
            replace_image(os.path.join(SA_RES, f'mipmap-{d}', f'{name}_sa.png'), plain)
    ring = ring_icon_svg('default')
    for d in DENSITIES:   # icon shown for the app's account in Android settings / contacts
        replace_image(os.path.join(RES, f'drawable-{d}', 'ic_launcher_dr.webp'), ring)


# ---- 3. small in-app bitmaps --------------------------------------------------
def make_small_bitmaps():
    # status-bar notification icon: 24 dp, white on transparent
    notif = SVG_HEAD.format(w=24, h=24) + f'<path d="{mark.placed(19.0, 12, 12)}" fill="#FFFFFF"/></svg>'
    # intro page 1 logo texture: 82 x 74, drawn so it lands in the middle of the sphere
    intro = SVG_HEAD.format(w=82, h=74) + f'<path d="{mark.placed(62.0, 47.0, 34.5)}" fill="#FFFFFF"/></svg>'
    # full-bleed logo discs
    disc68 = (SVG_HEAD.format(w=68, h=68) + f'<defs>{brand_gradient("bg", 0, 0, 68)}</defs>'
              f'<circle cx="34" cy="34" r="34" fill="url(#bg)"/><path d="{mark.placed(34.0, 34, 34)}" fill="#FFFFFF"/></svg>')
    disc15 = (SVG_HEAD.format(w=15, h=15) + f'<defs>{brand_gradient("bg", 0, 0, 15)}</defs>'
              f'<circle cx="7.5" cy="7.5" r="7.5" fill="url(#bg)"/><path d="{mark.placed(8.0, 7.5, 7.5)}" fill="#FFFFFF"/></svg>')
    for d in DENSITIES:
        base = os.path.join(RES, f'drawable-{d}')
        replace_image(os.path.join(base, 'notification.webp'), notif)
        replace_image(os.path.join(base, 'intro_tg_plane.webp'), intro)
        replace_image(os.path.join(base, 'logo_middle.webp'), disc68)
        replace_image(os.path.join(base, 'logo_middle.png'), disc68)
        replace_image(os.path.join(base, 'book_logo.webp'), disc15)


# ---- 4. vector drawables ------------------------------------------------------
def make_monochrome_icon():
    # themed-icon layer: 90 x 90 viewport stretched over the 108 dp canvas
    d = mark.placed(33.0 / 1.2, 45, 45, digits=2)
    write_text(os.path.join(RES, 'drawable', 'icon_plane.xml'),
               '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
               '    android:width="90dp"\n    android:height="90dp"\n'
               '    android:viewportWidth="90"\n    android:viewportHeight="90">\n'
               '  <path\n'
               f'      android:pathData="{d}"\n'
               '      android:fillColor="#FFFFFF"/>\n'
               '</vector>\n')


def make_icon_background():
    write_text(os.path.join(RES, 'drawable', 'icon_background_sa.xml'),
               '<?xml version="1.0" encoding="utf-8"?>\n'
               '<shape xmlns:android="http://schemas.android.com/apk/res/android">\n'
               '    <gradient\n        android:type="linear"\n        android:angle="90"\n'
               f'        android:startColor="{BRAND_BOTTOM}"\n        android:endColor="{BRAND_TOP}" />\n'
               '</shape>\n')


def wordmark_paths(cap_top, baseline, left, box_width):
    """Outline of WORDMARK_TEXT in DM Sans Bold.

    The original wordmark's capital letters run from cap_top to baseline. The new word keeps
    that band's centre line; if it would be wider than the box it is scaled down to fit.
    """
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from PIL import ImageFont

    font = instancer.instantiateVariableFont(TTFont(WORDMARK_FONT), {'wght': 700, 'opsz': 40})
    buf = io.BytesIO()
    font.save(buf)
    upm = font['head'].unitsPerEm
    cap = font['OS/2'].sCapHeight
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    # pen positions with kerning, measured at 1 px per font unit
    pil = ImageFont.truetype(io.BytesIO(buf.getvalue()), upm, layout_engine=ImageFont.Layout.RAQM)
    origins, ink_min, ink_max = [], None, None
    for i, ch in enumerate(WORDMARK_TEXT):
        origin = pil.getlength(WORDMARK_TEXT[:i + 1]) - pil.getlength(ch)
        origins.append(origin)
        rec = RecordingPen()
        glyphs[cmap[ord(ch)]].draw(rec)
        xs = [origin + pt[0] for _, args in rec.value for pt in args if pt is not None]
        ink_min = min(xs) if ink_min is None else min(ink_min, min(xs))
        ink_max = max(xs) if ink_max is None else max(ink_max, max(xs))
    scale = (baseline - cap_top) / cap
    available = box_width - 2 * left
    if (ink_max - ink_min) * scale > available:
        scale = available / (ink_max - ink_min)
    base = (cap_top + baseline) / 2.0 + cap * scale / 2.0   # same centre line as the original capitals
    parts = []
    for ch, origin in zip(WORDMARK_TEXT, origins):
        pen = SVGPathPen(glyphs, ntos=lambda v: f'{v:.2f}')
        tx = left + (origin - ink_min) * scale
        glyphs[cmap[ord(ch)]].draw(TransformPen(pen, (scale, 0, 0, -scale, tx, base)))
        parts.append(pen.getCommands())
    return ''.join(parts), left + (ink_max - ink_min) * scale


def make_wordmarks():
    if not os.path.exists(WORDMARK_FONT):
        print('  (wordmark font not found, keeping the existing wordmark files)')
        return
    # (file, viewport w, viewport h, width dp, height dp, cap top, baseline, left) - same boxes as the originals
    specs = [('telegram_logo.xml', 249, 57, '83dp', '19dp', 0.76, 43.0, 0.42),
             ('telegram_logo_2.xml', 269, 61, '90dp', '20.408922dp', 0.2, 45.9, 0.5)]
    for name, vw, vh, wdp, hdp, cap_top, baseline, left in specs:
        d, x_max = wordmark_paths(cap_top, baseline, left, vw)
        if x_max > vw:
            raise SystemExit(f'wordmark is wider than its box: {x_max:.1f} > {vw}')
        write_text(os.path.join(RES, 'drawable', name),
                   f'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:height="{hdp}" '
                   f'android:viewportHeight="{vh}" android:viewportWidth="{vw}" android:width="{wdp}">\n'
                   f'    <path android:fillColor="#FFFFFFFF" android:fillType="nonZero" android:pathData="{d}"/>\n'
                   '</vector>\n')


def make_splash():
    """Android 12+ splash animation: swap the circle colour and the logo shape's three paths."""
    path = os.path.join(RES, 'drawable', 'tg_splash_320.xml')
    with open(path, encoding='utf-8') as f:
        xml = f.read()
    end = mark.placed(100.0, 160, 160, digits=3)                 # resting place: centre of the 320 box
    start = mark.placed(100.0, 160 - 120, 160 + 120, digits=3)   # starts 120 units down-left, like the original
    # 1) colour of the circle, 2) the logo shape, 3) its move animation (from start to end)
    xml, n1 = re.subn(r'(android:name="circle".*?android:fillColor=")[^"]+(")',
                      lambda m: m.group(1) + BRAND_FLAT + m.group(2), xml, count=1, flags=re.S)
    xml, n2 = re.subn(r'(android:name="plane"\s+android:pathData=")[^"]+(")',
                      lambda m: m.group(1) + start + m.group(2), xml, count=1)
    xml, n3 = re.subn(r'(<target android:name="plane">.*?android:valueFrom=")[^"]+("\s+android:valueTo=")[^"]+(")',
                      lambda m: m.group(1) + start + m.group(2) + end + m.group(3), xml, count=1, flags=re.S)
    if (n1, n2, n3) != (1, 1, 1):
        raise SystemExit('tg_splash_320.xml does not look like the expected file')
    write_text(path, xml)


def make_qr_logo():
    write_text(os.path.join(RES, 'raw', 'qr_logo.svg'),
               '<?xml version="1.0" encoding="UTF-8"?><svg width="150px" height="150px" viewBox="0 0 150 150" version="1.1" '
               'xmlns="http://www.w3.org/2000/svg">'
               f'<circle id="Oval" fill="{BRAND_FLAT}" cx="75" cy="75" r="75" />'
               f'<path d="{mark.path_d(*mark.placed_transform(76.0, 75, 75), digits=3, sep=",")}" fill="#FFFFFF" /></svg>\n')


# ---- 5. animated logos (Lottie) used in QR codes and on the update screen -------
def lottie_shapes(height, cx=0.0, cy=0.0):
    """The mark as static Lottie bezier shapes centred on (cx, cy)."""
    scale, tx, ty = mark.placed_transform(height, cx, cy)
    shapes = []
    for n, contour in enumerate(mark.contours()):
        v, i_t, o_t = [], [], []
        for cmd, pts in contour:
            pts = [(x * scale + tx, y * scale + ty) for x, y in pts]
            if cmd in ('M', 'L'):
                v.append(list(pts[0])); i_t.append([0.0, 0.0]); o_t.append([0.0, 0.0])
            elif cmd == 'C':
                c1, c2, end = pts
                o_t[-1] = [c1[0] - v[-1][0], c1[1] - v[-1][1]]
                v.append(list(end)); i_t.append([c2[0] - end[0], c2[1] - end[1]]); o_t.append([0.0, 0.0])
        if len(v) > 1 and abs(v[0][0] - v[-1][0]) < 1e-6 and abs(v[0][1] - v[-1][1]) < 1e-6:
            i_t[0] = i_t[-1]            # last point repeats the first: fold it into the closed path
            v.pop(); i_t.pop(); o_t.pop()
        rnd = lambda arr: [[round(a, 3), round(b, 3)] for a, b in arr]
        shapes.append({'hd': False, 'nm': f'Path {n + 1}', 'ty': 'sh', 'ind': n,
                       'ks': {'a': 0, 'k': {'c': True, 'i': rnd(i_t), 'o': rnd(o_t), 'v': rnd(v)}}})
    return shapes


def hex_rgb(color):
    return [round(int(color[i:i + 2], 16) / 255.0, 3) for i in (1, 3, 5)]


def make_lottie_logos():
    import json
    top, bottom = hex_rgb(BRAND_TOP), hex_rgb(BRAND_BOTTOM)
    middle = [round((a + b) / 2, 3) for a, b in zip(top, bottom)]
    for name in ('qr_code_logo.json', 'plane_logo_plain.json'):
        path = os.path.join(RES, 'raw', name)
        with open(path, encoding='utf-8') as f:
            anim = json.load(f)
        kept = []
        for layer in anim['layers']:
            nm = layer.get('nm')
            if nm == 'Null 2':
                layer['ks']['p'] = {'a': 0, 'k': [256, 256, 0]}
            elif nm == 'Null 1':
                layer['ks']['p'] = {'a': 0, 'k': [0, 0, 0]}
            elif nm in ('Plane', 'Mark'):
                layer['nm'] = 'Mark'
                layer['ks']['a'] = {'a': 0, 'k': [0, 0, 0]}
                layer['ks']['p'] = {'a': 0, 'k': [0, 0, 0]}
                # gentle rocking, same keyframe layout as the original rotation track
                layer['ks']['r'] = {'a': 1, 'k': [
                    {'t': 20, 'i': {'x': [0.69], 'y': [1]}, 'o': {'x': [0.31], 'y': [0]}, 's': [-5]},
                    {'t': 47, 'i': {'x': [0.69], 'y': [1]}, 'o': {'x': [0.31], 'y': [0]}, 's': [5]},
                    {'t': 73, 's': [-5]}]}
                group = layer['shapes'][0]
                rest = [it for it in group['it'] if it.get('ty') != 'sh']
                group['it'] = lottie_shapes(215.0) + rest
            elif nm == 'Shape Layer 17':            # the coloured disc behind the logo
                for it in layer['shapes'][0]['it']:
                    if it.get('ty') == 'gf':
                        it['g'] = {'p': 3, 'k': {'a': 0, 'k': [0] + top + [0.5] + middle + [1] + bottom}}
                        it['s'] = {'a': 0, 'k': [0, -201]}     # run the gradient over the whole disc,
                        it['e'] = {'a': 0, 'k': [0, 213]}      # top edge to bottom edge
            else:
                continue                              # wind streaks of the old flying logo
            kept.append(layer)
        anim['layers'] = kept
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(anim, f, separators=(',', ':'))
        written.append(os.path.relpath(path, ROOT))


def main():
    make_foregrounds()
    make_legacy_icons()
    make_small_bitmaps()
    make_monochrome_icon()
    make_icon_background()
    make_wordmarks()
    make_splash()
    make_qr_logo()
    make_lottie_logos()
    make_extra_icons()
    print(f'{len(written)} files written')
    for p in written:
        print('  ', p)


if __name__ == '__main__':
    main()
