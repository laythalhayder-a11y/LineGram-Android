"""LineGram logo mark: a bold rounded "L" hugging a small chat bubble.

Design box is 100 x 100 units. Everything is built from M / L / C / Z only, so the
same outline can be used for PNG rendering, Android VectorDrawables (including
path-morph animations) and Lottie shapes.
"""

K = 0.5523  # cubic control-point factor for a quarter circle

# ---- geometry (design units) -------------------------------------------------
STEM_X = 33.0      # centre line of the vertical stroke
STEM_TOP = 27.0    # centre of the top round cap
FOOT_Y = 70.0      # centre line of the horizontal stroke
FOOT_END = 70.0    # centre of the right round cap
HALF = 7.5         # half stroke width
INNER_R = 4.0      # radius of the concave inner corner

BUB_X0, BUB_Y0, BUB_X1, BUB_Y1, BUB_R = 49.0, 20.0, 78.0, 46.0, 9.0
TAIL = ((69.0, 46.0), (58.5, 55.5), (59.5, 46.0))  # base right, tip, base left

BBOX = (STEM_X - HALF, STEM_TOP - HALF, BUB_X1, FOOT_Y + HALF)   # x0, y0, x1, y1
WIDTH = BBOX[2] - BBOX[0]
HEIGHT = BBOX[3] - BBOX[1]
OPTICAL_CENTER = (50.6, 49.0)   # between bounding-box centre and area centroid


def contours():
    """Two closed contours: [(cmd, [points...]), ...] for the L and for the bubble."""
    h, k = HALF, HALF * K
    ki = INNER_R * K
    xl, xr = STEM_X - h, STEM_X + h
    yt, yb = FOOT_Y - h, FOOT_Y + h
    L = [
        ('M', [(xl, STEM_TOP)]),
        ('C', [(xl, STEM_TOP - k), (STEM_X - k, STEM_TOP - h), (STEM_X, STEM_TOP - h)]),
        ('C', [(STEM_X + k, STEM_TOP - h), (xr, STEM_TOP - k), (xr, STEM_TOP)]),
        ('L', [(xr, yt - INNER_R)]),
        ('C', [(xr, yt - INNER_R + ki), (xr + INNER_R - ki, yt), (xr + INNER_R, yt)]),
        ('L', [(FOOT_END, yt)]),
        ('C', [(FOOT_END + k, yt), (FOOT_END + h, FOOT_Y - k), (FOOT_END + h, FOOT_Y)]),
        ('C', [(FOOT_END + h, FOOT_Y + k), (FOOT_END + k, yb), (FOOT_END, yb)]),
        ('L', [(STEM_X, yb)]),
        ('C', [(STEM_X - k, yb), (xl, FOOT_Y + k), (xl, FOOT_Y)]),
        ('Z', []),
    ]
    r, kb = BUB_R, BUB_R * K
    x0, y0, x1, y1 = BUB_X0, BUB_Y0, BUB_X1, BUB_Y1
    B = [
        ('M', [(x0 + r, y0)]),
        ('L', [(x1 - r, y0)]),
        ('C', [(x1 - r + kb, y0), (x1, y0 + r - kb), (x1, y0 + r)]),
        ('L', [(x1, y1 - r)]),
        ('C', [(x1, y1 - r + kb), (x1 - r + kb, y1), (x1 - r, y1)]),
        ('L', [TAIL[0]]),
        ('L', [TAIL[1]]),
        ('L', [TAIL[2]]),
        ('L', [(x0 + r, y1)]),
        ('C', [(x0 + r - kb, y1), (x0, y1 - r + kb), (x0, y1 - r)]),
        ('L', [(x0, y0 + r)]),
        ('C', [(x0, y0 + r - kb), (x0 + r - kb, y0), (x0 + r, y0)]),
        ('Z', []),
    ]
    return [L, B]


def path_d(scale=1.0, tx=0.0, ty=0.0, digits=3, sep=','):
    """SVG / VectorDrawable path data for the whole mark after scale + translate."""
    out = []
    for contour in contours():
        for cmd, pts in contour:
            if not pts:
                out.append(cmd)
            else:
                out.append(cmd + ' '.join(f'{x * scale + tx:.{digits}f}{sep}{y * scale + ty:.{digits}f}' for x, y in pts))
    return ' '.join(out)


def placed(height, cx, cy, digits=3):
    """Path data with the mark `height` tall and its optical centre at (cx, cy)."""
    s = height / HEIGHT
    return path_d(s, cx - OPTICAL_CENTER[0] * s, cy - OPTICAL_CENTER[1] * s, digits)


def placed_transform(height, cx, cy):
    s = height / HEIGHT
    return s, cx - OPTICAL_CENTER[0] * s, cy - OPTICAL_CENTER[1] * s
