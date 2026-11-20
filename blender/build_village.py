"""Genera el pueblo de "Antes del amanecer" con Blender (bpy) y lo exporta a GLB + layout.json.

Coordenadas: se escriben en el sistema de Three.js (x este, y arriba, z sur) y se
convierten a Blender (X=x, Y=-z, Z=y). El exportador glTF las devuelve a Three.js.
"""
import bpy, bmesh, math, random, json, os, sys

OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/home/claude/v2/out'
os.makedirs(OUT, exist_ok=True)
random.seed(1889)

# ------------------------------------------------------------------ builder
class B:
    def __init__(self, name):
        self.name = name; self.v = []; self.f = []; self.c = []
    def add(self, pts, faces, col):
        base = len(self.v)
        for (x, y, z) in pts:
            self.v.append((x, -z, y))
        for fc in faces:
            self.f.append(tuple(base + i for i in fc))
            self.c.append(col)

def jit(col, a=0.06):
    return tuple(max(0, min(1, c + random.uniform(-a, a))) for c in col)

def xf(cx, cy, cz, r):
    cr, sr = math.cos(r), math.sin(r)
    return lambda lx, ly, lz: (cx + lx * cr + lz * sr, cy + ly, cz - lx * sr + lz * cr)

def box(b, cx, cy, cz, sx, sy, sz, r, col, bottom=False, top=True):
    T = xf(cx, cy, cz, r); hx, hy, hz = sx / 2, sy / 2, sz / 2
    P = [T(-hx, -hy, hz), T(hx, -hy, hz), T(hx, hy, hz), T(-hx, hy, hz),
         T(hx, -hy, -hz), T(-hx, -hy, -hz), T(-hx, hy, -hz), T(hx, hy, -hz)]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (1, 4, 7, 2), (5, 0, 3, 6)]
    if top: F.append((3, 2, 7, 6))
    if bottom: F.append((5, 4, 1, 0))
    b.add(P, F, col)

def quad(b, T, a, bb, c, d, col):
    b.add([T(*a), T(*bb), T(*c), T(*d)], [(0, 1, 2, 3)], col)

def gable(b, cx, cy, cz, W, D, R, r, col, endcol=None):
    T = xf(cx, cy, cz, r)
    A, Bp, C, Dd, E, F = (-W/2, 0, D/2), (W/2, 0, D/2), (W/2, R, 0), (-W/2, R, 0), (-W/2, 0, -D/2), (W/2, 0, -D/2)
    b.add([T(*A), T(*Bp), T(*C), T(*Dd)], [(0, 1, 2, 3)], col)
    b.add([T(*F), T(*E), T(*Dd), T(*C)], [(0, 1, 2, 3)], col)
    ec = endcol or col
    b.add([T(*Bp), T(*F), T(*C)], [(0, 1, 2)], ec)
    b.add([T(*E), T(*A), T(*Dd)], [(0, 1, 2)], ec)

def cyl(b, cx, cy, cz, r0, r1, h, seg, col, top=True):
    P = []
    for i in range(seg):
        a = i / seg * math.tau
        P.append((cx + r0 * math.sin(a), cy, cz + r0 * math.cos(a)))
    for i in range(seg):
        a = i / seg * math.tau
        P.append((cx + r1 * math.sin(a), cy + h, cz + r1 * math.cos(a)))
    F = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
    if top and r1 > 0.001:
        P.append((cx, cy + h, cz)); c = len(P) - 1
        F += [(c, seg + i, seg + (i + 1) % seg) for i in range(seg)]
    b.add(P, F, col)

def pyramid(b, cx, cy, cz, w, h, r, col):
    T = xf(cx, cy, cz, r); s = w / 2
    P = [T(-s, 0, s), T(s, 0, s), T(s, 0, -s), T(-s, 0, -s), T(0, h, 0)]
    b.add(P, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], col)

def sphere(b, cx, cy, cz, rad, col, seg=10, rings=7, sy=1.0):
    P = []; F = []
    for j in range(rings + 1):
        th = j / rings * math.pi
        for i in range(seg):
            ph = i / seg * math.tau
            P.append((cx + rad * math.sin(th) * math.sin(ph), cy + rad * sy * math.cos(th), cz + rad * math.sin(th) * math.cos(ph)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i; bq = j * seg + (i + 1) % seg
            F.append((a, a + seg, bq + seg, bq))
    b.add(P, F, col)

# ------------------------------------------------------------------ palette
WALLS = [(0.85, 0.64, 0.26), (0.91, 0.84, 0.66), (0.56, 0.70, 0.79), (0.85, 0.55, 0.45), (0.66, 0.76, 0.60),
         (0.90, 0.76, 0.36), (0.66, 0.61, 0.77), (0.80, 0.78, 0.72), (0.93, 0.72, 0.50)]
ROOFS = [(0.71, 0.34, 0.18), (0.24, 0.35, 0.54), (0.62, 0.30, 0.20), (0.30, 0.42, 0.62), (0.55, 0.36, 0.30)]
SHUT = [(0.20, 0.42, 0.30), (0.18, 0.32, 0.55), (0.45, 0.55, 0.25), (0.55, 0.22, 0.18)]
DARKWIN = (0.07, 0.10, 0.20)
FRAME = (0.30, 0.24, 0.20)
DOOR = [(0.32, 0.20, 0.12), (0.15, 0.30, 0.25), (0.20, 0.25, 0.45), (0.45, 0.18, 0.14)]
GLOWC = [(1.0, 0.80, 0.30), (1.0, 0.70, 0.25), (1.0, 0.86, 0.42), (0.98, 0.62, 0.20)]
POST = (0.10, 0.16, 0.14)

build = B('build'); glow = B('glow'); street = B('street'); churchwin = B('churchwin')

# ------------------------------------------------------------------ layout
STREETS = [
    {'name': 'Calle Mayor', 'hw': 3.4, 'pts': [(0, 64), (1.5, 48), (-1.5, 32), (1.0, 18), (0, 8)]},
    {'name': 'Calle del Viento', 'hw': 2.7, 'pts': [(-12, -5), (-28, -8), (-44, -4), (-58, 3), (-70, 6)]},
    {'name': 'Calle del Horno', 'hw': 2.7, 'pts': [(12, -4), (28, -1), (44, -7), (58, -3), (70, 4)]},
    {'name': 'Pasaje', 'hw': 2.0, 'pts': [(-1.0, 30), (-14, 29), (-27, 24), (-31, 12), (-29, -6)]},
    {'name': 'Callejón', 'hw': 2.0, 'pts': [(1.0, 40), (14, 38), (26, 30), (30, 16), (28, -2)]},
]
PLAZA = {'x': 0, 'z': -6, 'r': 15}
CHURCH = {'x': 0, 'z': -30, 'w': 10, 'd': 18}   # centro de la nave
VILLAGE = {'cx': 0, 'cz': 4, 'rx': 70, 'rz': 64}

def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b; dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L2))
    qx, qz = ax + t * dx, az + t * dz
    return math.hypot(px - qx, pz - qz)

def street_dist(px, pz):
    best = 1e9
    for s in STREETS:
        for i in range(len(s['pts']) - 1):
            best = min(best, seg_dist(px, pz, s['pts'][i], s['pts'][i + 1]) - s['hw'])
    return best

houses = []
def corners(h):
    cx, cz, hw, hd, r = h['x'], h['z'], h['hw'], h['hd'], h['rot']
    cr, sr = math.cos(r), math.sin(r)
    out = []
    for lx, lz in [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd), (0, 0), (0, hd), (0, -hd), (-hw, 0), (hw, 0)]:
        out.append((cx + lx * cr + lz * sr, cz - lx * sr + lz * cr))
    return out
def inside(h, px, pz, m=0.0):
    dx, dz = px - h['x'], pz - h['z']; cr, sr = math.cos(h['rot']), math.sin(h['rot'])
    lx = dx * cr - dz * sr; lz = dx * sr + dz * cr
    return abs(lx) < h['hw'] + m and abs(lz) < h['hd'] + m
def in_church(px, pz, m=1.5):
    return abs(px - CHURCH['x']) < CHURCH['w'] / 2 + m + 1 and (CHURCH['z'] - CHURCH['d'] / 2 - m) < pz < (CHURCH['z'] + CHURCH['d'] / 2 + 6 + m)
def ok_house(h):
    cs = corners(h)
    for (px, pz) in cs:
        if street_dist(px, pz) < 0.05: return False
        if math.hypot(px - PLAZA['x'], pz - PLAZA['z']) < PLAZA['r'] + 0.5: return False
        if in_church(px, pz): return False
        e = ((px - VILLAGE['cx']) / VILLAGE['rx']) ** 2 + ((pz - VILLAGE['cz']) / VILLAGE['rz']) ** 2
        if e > 0.95: return False
        for o in houses:
            if inside(o, px, pz, -0.15): return False
    for o in houses:
        for (px, pz) in corners(o):
            if inside(h, px, pz, -0.15): return False
    return True

def make_house(h):
    T = xf(h['x'], 0, h['z'], h['rot'])
    hw, hd, fl = h['hw'], h['hd'], h['floors']
    H = 3.4 + (fl - 1) * 3.0
    wall = jit(random.choice(WALLS), 0.05); h['wall'] = wall
    roofc = jit(random.choice(ROOFS), 0.04)
    box(build, h['x'], H / 2, h['z'], hw * 2, H, hd * 2, h['rot'], wall)
    # cornisa
    tr = jit((min(1, wall[0] + .12), min(1, wall[1] + .12), min(1, wall[2] + .1)), .02)
    cx, cy, cz = T(0, H - 0.1, 0)
    box(build, cx, cy, cz, hw * 2 + 0.25, 0.22, hd * 2 + 0.25, h['rot'], tr)
    # techo
    R = hd * 2 * 0.32
    cx, cy, cz = T(0, H, 0)
    gable(build, cx, cy, cz, hw * 2 + 0.7, hd * 2 + 0.9, R, h['rot'], roofc, wall)
    if random.random() < 0.7:
        lx = random.uniform(-hw + 0.8, hw - 0.8)
        cx, cy, cz = T(lx, H + R * 0.6, -hd * 0.35)
        box(build, cx, cy, cz, 0.6, 1.6, 0.6, h['rot'], jit((0.62, 0.40, 0.30), .05))
        cx, cy, cz = T(lx, H + R * 0.6 + 0.85, -hd * 0.35)
        box(build, cx, cy, cz, 0.75, 0.12, 0.75, h['rot'], (0.35, 0.28, 0.25))
    # fachada (frente local +z)
    n = max(1, int((hw * 2 - 0.6) // 2.3))
    xs = [(-hw + (i + 0.5) * (hw * 2 / n)) for i in range(n)]
    shutters = random.random() < 0.65; shc = jit(random.choice(SHUT), .04)
    door_i = random.randrange(n); h['door'] = None
    shop = h.get('shop') or (random.random() < 0.18 and fl >= 2)
    lit_p = h.get('lit', 0.6)
    for f in range(fl):
        y = 1.55 if f == 0 else 3.4 + (f - 1) * 3.0 + 1.55
        for i, lx in enumerate(xs):
            if f == 0 and i == door_i:
                dc = jit(random.choice(DOOR), .04)
                cx, cy, cz = T(lx, 1.15, hd + 0.05); box(build, cx, cy, cz, 1.35, 2.5, 0.12, h['rot'], FRAME)
                cx, cy, cz = T(lx, 1.1, hd + 0.11); box(build, cx, cy, cz, 1.1, 2.2, 0.06, h['rot'], dc)
                cx, cy, cz = T(lx, 0.06, hd + 0.35); box(build, cx, cy, cz, 1.6, 0.12, 0.6, h['rot'], (0.55, 0.52, 0.55))
                h['door'] = T(lx, 0, hd + 1.4)
                continue
            if f == 0 and shop:
                cx, cy, cz = T(lx, 1.45, hd + 0.05); box(build, cx, cy, cz, 1.8, 2.1, 0.1, h['rot'], FRAME)
                g = h.get('shopcol', random.choice(GLOWC))
                quad(glow, T, (lx - 0.8, 0.5, hd + 0.11), (lx + 0.8, 0.5, hd + 0.11), (lx + 0.8, 2.4, hd + 0.11), (lx - 0.8, 2.4, hd + 0.11), g)
                continue
            lit = random.random() < lit_p
            cx, cy, cz = T(lx, y, hd + 0.04); box(build, cx, cy, cz, 1.2, 1.6, 0.08, h['rot'], FRAME)
            pane = (lx - 0.48, y - 0.68, hd + 0.085), (lx + 0.48, y - 0.68, hd + 0.085), (lx + 0.48, y + 0.68, hd + 0.085), (lx - 0.48, y + 0.68, hd + 0.085)
            if lit:
                quad(glow, T, *pane, jit(random.choice(GLOWC), .03))
                cx, cy, cz = T(lx, y, hd + 0.09); box(build, cx, cy, cz, 0.06, 1.36, 0.03, h['rot'], FRAME)
            else:
                quad(build, T, *pane, DARKWIN)
                if shutters:
                    for s in (-1, 1):
                        cx, cy, cz = T(lx + s * 0.9, y, hd + 0.07); box(build, cx, cy, cz, 0.55, 1.6, 0.07, h['rot'], shc)
            cx, cy, cz = T(lx, y - 0.86, hd + 0.13); box(build, cx, cy, cz, 1.35, 0.1, 0.26, h['rot'], tr)
    if shop:
        aw = h.get('awning', random.choice([(0.85, 0.25, 0.18), (0.20, 0.45, 0.35), (0.92, 0.72, 0.20), (0.25, 0.32, 0.62)]))
        T2 = xf(*T(0, 2.9, hd + 0.9), h['rot'])
        A = (-hw + 0.2, 0.25, -0.85); Bq = (hw - 0.2, 0.25, -0.85); C = (hw - 0.2, -0.25, 0.85); D = (-hw + 0.2, -0.25, 0.85)
        build.add([T2(*D), T2(*C), T2(*Bq), T2(*A)], [(0, 1, 2, 3)], aw)
        build.add([T2(*A), T2(*Bq), T2(*C), T2(*D)], [(0, 1, 2, 3)], aw)
        quad(build, T2, (-hw + 0.2, -0.55, 0.85), (hw - 0.2, -0.55, 0.85), (hw - 0.2, -0.25, 0.85), (-hw + 0.2, -0.25, 0.85), aw)
    if fl >= 2 and random.random() < 0.3:
        lx = xs[len(xs) // 2]
        cx, cy, cz = T(lx, 3.45, hd + 0.5); box(build, cx, cy, cz, 2.0, 0.14, 1.0, h['rot'], (0.45, 0.42, 0.45))
        for k in range(5):
            cx, cy, cz = T(lx - 0.9 + k * 0.45, 3.95, hd + 0.95); box(build, cx, cy, cz, 0.05, 0.9, 0.05, h['rot'], POST)
        cx, cy, cz = T(lx, 4.4, hd + 0.95); box(build, cx, cy, cz, 2.0, 0.06, 0.06, h['rot'], POST)
    # hastiales con alguna ventana
    for side in (-1, 1):
        if random.random() < 0.5 and fl >= 2:
            y = 3.4 + 1.55
            T3 = xf(*T(side * (hw + 0.04), 0, 0), h['rot'] + side * math.pi / 2)
            if random.random() < lit_p:
                quad(glow, T3, (-0.45, y - 0.6, 0.02), (0.45, y - 0.6, 0.02), (0.45, y + 0.6, 0.02), (-0.45, y + 0.6, 0.02), jit(random.choice(GLOWC), .03))
            else:
                quad(build, T3, (-0.45, y - 0.6, 0.02), (0.45, y - 0.6, 0.02), (0.45, y + 0.6, 0.02), (-0.45, y + 0.6, 0.02), DARKWIN)
    if h['door'] is None:
        h['door'] = T(xs[0], 0, hd + 1.4)
    return h

def place_row(s, side):
    pts = s['pts']
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, bz - az); tx, tz = (bx - ax) / L, (bz - az) / L
        nx, nz = -tz * side, tx * side
        u = 1.0
        while u < L - 1.0:
            placed = False
            for w, d in ((random.uniform(5.5, 8.0), random.uniform(7.5, 10)), (random.uniform(4.5, 6), random.uniform(5.5, 7)), (4.2, 4.8)):
                if u + w > L + 1.0: continue
                cu = u + w / 2; off = s['hw'] + 0.2 + d / 2
                cx, cz = ax + tx * cu + nx * off, az + tz * cu + nz * off
                rot = math.atan2(-nx, -nz)
                h = {'x': cx, 'z': cz, 'hw': w / 2, 'hd': d / 2, 'rot': rot, 'floors': random.choice([2, 2, 3, 3, 2, 1])}
                if ok_house(h):
                    houses.append(h); u += w + random.choice([0, 0, 0, 0.15, 0.8]); placed = True; break
            if not placed: u += 0.8

# casas especiales primero (vecinos)
SPECIAL = {}
def special(key, x, z, rot, w, d, fl, **kw):
    h = {'x': x, 'z': z, 'hw': w / 2, 'hd': d / 2, 'rot': rot, 'floors': fl, **kw}
    houses.append(h); SPECIAL[key] = h
# Roulin: frente a la plaza, lado este, mirando al centro de la plaza
ang = math.radians(40); r = PLAZA['r'] + 0.3 + 4.0
rx_, rz_ = PLAZA['x'] + r * math.cos(ang), PLAZA['z'] - r * math.sin(ang)
special('roulin', rx_, rz_, math.atan2(PLAZA['x'] - rx_, PLAZA['z'] - rz_), 7, 8, 2, lit=0.9)
# Augustine: Calle del Viento, lado norte
special('aug', -36, -6 - 2.7 - 0.2 - 4.0, 0, 7, 8, 2, lit=0.8)
# panadería: Calle del Horno, lado sur
special('pan', 36, -4 + 2.7 + 0.2 + 4.5, math.pi, 8, 9, 2, lit=0.6, shop=True, shopcol=(1.0, 0.55, 0.15), awning=(0.80, 0.30, 0.15))
# café de la terraza: plaza, lado oeste (homenaje a "Terraza de café por la noche")
cr_ = PLAZA['r'] + 0.3 + 4.5
special('cafe', PLAZA['x'] - cr_ * math.cos(math.radians(-25)), PLAZA['z'] + cr_ * math.sin(math.radians(-25)), 0, 9, 9, 3, lit=0.9, shop=True, shopcol=(1.0, 0.82, 0.30), awning=(0.95, 0.78, 0.18))
SPECIAL['cafe']['rot'] = math.atan2(PLAZA['x'] - SPECIAL['cafe']['x'], PLAZA['z'] - SPECIAL['cafe']['z'])

# anillo de la plaza
for deg in range(0, 360, 22):
    a = math.radians(deg)
    w, d = random.uniform(6, 8), random.uniform(7, 9)
    rr = PLAZA['r'] + 0.3 + d / 2
    x, z = PLAZA['x'] + rr * math.sin(a), PLAZA['z'] + rr * math.cos(a)
    h = {'x': x, 'z': z, 'hw': w / 2, 'hd': d / 2, 'rot': math.atan2(PLAZA['x'] - x, PLAZA['z'] - z), 'floors': random.choice([2, 3, 3])}
    cs = corners(h)
    if all(street_dist(px, pz) > 0.05 and not in_church(px, pz) for px, pz in cs) and not any(inside(o, px, pz, -0.15) for o in houses for px, pz in cs) and not any(inside(h, px, pz, -0.15) for o in houses for px, pz in corners(o)):
        houses.append(h)

for s in STREETS:
    place_row(s, 1); place_row(s, -1)
# relleno detrás de las filas
for _ in range(500):
    x = random.uniform(-62, 62); z = random.uniform(-52, 60)
    rot = random.choice([0, math.pi / 2, math.pi, -math.pi / 2]) + random.uniform(-0.1, 0.1)
    h = {'x': x, 'z': z, 'hw': random.uniform(2.5, 4), 'hd': random.uniform(3.5, 5), 'rot': rot, 'floors': random.choice([1, 2, 2]), 'lit': 0.3}
    if street_dist(x, z) > 7 and ok_house(h):
        houses.append(h)

for h in houses:
    make_house(h)
print('houses', len(houses))

# ------------------------------------------------------------------ iglesia
cx, cz, cw, cd = CHURCH['x'], CHURCH['z'], CHURCH['w'], CHURCH['d']
CW = (0.58, 0.62, 0.70); CR = (0.22, 0.30, 0.48)
box(build, cx, 5, cz, cw, 10, cd, 0, CW)
gable(build, cx, 10, cz, cd + 0.8, cw + 0.8, 4, math.pi / 2, CR, CW)
fz = cz + cd / 2
box(build, cx, 8, fz + 2.2, 4.6, 16, 4.6, 0, (0.62, 0.66, 0.74))
box(build, cx, 16.2, fz + 2.2, 5.2, 0.4, 5.2, 0, (0.75, 0.76, 0.80))
pyramid(build, cx, 16.4, fz + 2.2, 4.4, 13, 0, (0.30, 0.38, 0.55))
box(build, cx, 1.6, fz + 4.55, 2.2, 3.4, 0.2, 0, FRAME)
box(build, cx, 1.5, fz + 4.62, 1.8, 3.0, 0.1, 0, (0.18, 0.12, 0.10))
# ventanas de la iglesia (oscuras al principio, se encienden en el juego)
Tf = xf(cx, 0, fz + 4.52, 0)
for y in (6.5, 10.5, 14.0):
    quad(churchwin, Tf, (-0.45, y - 1.0, 0.04), (0.45, y - 1.0, 0.04), (0.45, y + 1.0, 0.04), (-0.45, y + 1.0, 0.04), (1.0, 0.84, 0.36))
for side in (-1, 1):
    Ts = xf(cx + side * (cw / 2 + 0.03), 0, cz, side * math.pi / 2)
    for k in range(5):
        u = -cd / 2 + 2 + k * (cd - 4) / 4
        quad(churchwin, Ts, (u - 0.5, 3.0, 0.02), (u + 0.5, 3.0, 0.02), (u + 0.5, 7.2, 0.02), (u - 0.5, 7.2, 0.02), (1.0, 0.80, 0.32))
CHURCH_DOOR = (cx, 0, fz + 6.2)
STEEPLE = (cx, 14.3, fz + 4.9)

# ------------------------------------------------------------------ plaza: fuente, bancos, mesas del café
cyl(build, PLAZA['x'], 0, PLAZA['z'], 2.4, 2.4, 0.6, 16, (0.60, 0.58, 0.62))
cyl(build, PLAZA['x'], 0.6, PLAZA['z'], 2.2, 2.2, 0.02, 16, (0.20, 0.32, 0.55))
cyl(build, PLAZA['x'], 0, PLAZA['z'], 0.35, 0.3, 2.2, 8, (0.62, 0.60, 0.64))
cyl(build, PLAZA['x'], 2.2, PLAZA['z'], 0.9, 0.2, 0.4, 10, (0.62, 0.60, 0.64))
for deg in (60, 120, 240, 300):
    a = math.radians(deg); x, z = PLAZA['x'] + 7 * math.sin(a), PLAZA['z'] + 7 * math.cos(a)
    rot = math.atan2(PLAZA['x'] - x, PLAZA['z'] - z)
    box(build, x, 0.45, z, 2.2, 0.1, 0.6, rot, (0.42, 0.28, 0.16))
    T = xf(x, 0, z, rot); bx, by, bz = T(0, 0.75, -0.3); box(build, bx, by, bz, 2.2, 0.5, 0.08, rot, (0.42, 0.28, 0.16))
    for s in (-1, 1):
        bx, by, bz = T(s * 0.95, 0.22, 0); box(build, bx, by, bz, 0.1, 0.45, 0.5, rot, POST)
cafe = SPECIAL['cafe']; Tc = xf(cafe['x'], 0, cafe['z'], cafe['rot'])
for (lx, lz) in [(-3, 3.2), (0, 3.6), (3, 3.2), (-1.5, 6.0), (1.8, 6.2)]:
    tx, ty, tz = Tc(lx, 0, cafe['hd'] + lz)
    cyl(build, tx, 0, tz, 0.06, 0.06, 0.75, 6, POST)
    cyl(build, tx, 0.75, tz, 0.45, 0.45, 0.05, 10, (0.92, 0.88, 0.78))
    for k in range(2):
        a = k * math.pi + cafe['rot']; sx, sz = tx + 0.7 * math.sin(a), tz + 0.7 * math.cos(a)
        box(build, sx, 0.45, sz, 0.4, 0.06, 0.4, a, (0.35, 0.22, 0.12))

# ------------------------------------------------------------------ faroles
lamps = []
def lamp(x, z, rot=0):
    cyl(build, x, 0, z, 0.12, 0.08, 3.6, 6, POST)
    cyl(build, x, 0, z, 0.22, 0.18, 0.4, 6, POST)
    box(build, x, 3.75, z, 0.5, 0.06, 0.5, rot, POST)
    T = xf(x, 3.75, z, rot)
    for (a, bq) in [((-0.2, 0.05, 0.2), (0.2, 0.05, 0.2)), ((0.2, 0.05, -0.2), (-0.2, 0.05, -0.2))]:
        pass
    box(glow, x, 4.05, z, 0.38, 0.55, 0.38, rot, (1.0, 0.86, 0.45))
    pyramid(build, x, 4.32, z, 0.6, 0.35, rot, POST)
    lamps.append((round(x, 2), 4.05, round(z, 2)))
def ok_lamp(x, z):
    if math.hypot(x - PLAZA['x'], z - PLAZA['z']) < 3.5: return False
    return not any(inside(h, x, z, 0.3) for h in houses) and not in_church(x, z, 0.3)
for s in STREETS:
    pts = s['pts']; acc = 6.0; side = 1
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, bz - az); tx, tz = (bx - ax) / L, (bz - az) / L
        while acc < L:
            off = (s['hw'] - 0.5) * side
            x, z = ax + tx * acc - tz * off, az + tz * acc + tx * off
            if ok_lamp(x, z): lamp(x, z, math.atan2(tx, tz))
            acc += 13; side *= -1
        acc -= L
for deg in range(0, 360, 60):
    a = math.radians(deg + 30); x, z = PLAZA['x'] + 11.5 * math.sin(a), PLAZA['z'] + 11.5 * math.cos(a)
    if ok_lamp(x, z): lamp(x, z)
print('lamps', len(lamps))

# ------------------------------------------------------------------ calles empedradas
COB = (0.58, 0.52, 0.62)
for s in STREETS:
    pts = s['pts']; hw = s['hw'] + 0.25
    dense = []
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, bz - az); n = max(1, int(L / 2))
        for k in range(n):
            t = k / n; dense.append((ax + (bx - ax) * t, az + (bz - az) * t))
    dense.append(pts[-1])
    for i in range(len(dense) - 1):
        (ax, az), (bx, bz) = dense[i], dense[i + 1]
        L = math.hypot(bx - ax, bz - az); tx, tz = (bx - ax) / L, (bz - az) / L; nx, nz = -tz, tx
        P = [(ax + nx * hw, 0.03, az + nz * hw), (ax - nx * hw, 0.03, az - nz * hw), (bx - nx * hw, 0.03, bz - nz * hw), (bx + nx * hw, 0.03, bz + nz * hw)]
        # orientar hacia arriba
        street.add(P, [(0, 1, 2, 3)] if ((P[1][0] - P[0][0]) * (P[3][2] - P[0][2]) - (P[1][2] - P[0][2]) * (P[3][0] - P[0][0])) < 0 else [(3, 2, 1, 0)], jit(COB, 0.03))
seg = 40; Pp = [(PLAZA['x'], 0.035, PLAZA['z'])]
for i in range(seg):
    a = i / seg * math.tau; Pp.append((PLAZA['x'] + (PLAZA['r'] + 1) * math.sin(a), 0.035, PLAZA['z'] + (PLAZA['r'] + 1) * math.cos(a)))
street.add(Pp, [(0, i + 1, (i + 1) % seg + 1) for i in range(seg)], COB)
# atrio frente a la iglesia
street.add([(cx - 6, 0.034, fz + 9), (cx + 6, 0.034, fz + 9), (cx + 6, 0.034, fz - 1), (cx - 6, 0.034, fz - 1)], [(0, 1, 2, 3)], COB)

# ------------------------------------------------------------------ personajes (estilo "pintado", abrigos largos)
SKIN = (0.93, 0.74, 0.58)
def figure(name, coat, hat='bowler', scarf=(0.75, 0.2, 0.15), beard=None, apron=False, baby=False, dress=False, cap=None):
    f = B(name); dk = tuple(c * 0.7 for c in coat)
    box(f, -0.1, 0.07, 0.05, 0.14, 0.14, 0.3, 0, (0.12, 0.1, 0.1)); box(f, 0.1, 0.07, 0.05, 0.14, 0.14, 0.3, 0, (0.12, 0.1, 0.1))
    cyl(f, 0, 0.1, 0, 0.42 if dress else 0.34, 0.21, 1.25, 10, coat)
    cyl(f, 0, 1.33, 0, 0.23, 0.15, 0.13, 10, coat)
    if apron:
        T = xf(0, 0, 0.0, 0); quad(f, T, (-0.24, 0.35, 0.33), (0.24, 0.35, 0.33), (0.18, 1.25, 0.24), (-0.18, 1.25, 0.24), (0.95, 0.93, 0.88))
    if not dress:
        for k in range(3): box(f, 0, 0.75 + k * 0.18, 0.255 - k * 0.012, 0.04, 0.04, 0.02, 0, (0.95, 0.8, 0.3) if cap else dk)
    if baby:
        for s in (-1, 1):
            cyl(f, s * 0.24, 1.0, 0.02, 0.06, 0.07, 0.36, 6, dk)
        box(f, 0, 1.05, 0.25, 0.5, 0.12, 0.16, 0, dk)
        sphere(f, 0, 1.12, 0.3, 0.16, (0.95, 0.93, 0.85), 8, 6, 0.7); sphere(f, 0.1, 1.17, 0.38, 0.06, SKIN, 6, 4)
    else:
        for s in (-1, 1):
            cyl(f, s * 0.27, 0.72, 0, 0.07, 0.085, 0.64, 6, dk); sphere(f, s * 0.27, 0.69, 0, 0.06, SKIN, 6, 4)
    cyl(f, 0, 1.40, 0, 0.14, 0.12, 0.08, 10, scarf)
    sphere(f, 0, 1.6, 0, 0.13, SKIN, 10, 7, 1.12)
    if beard:
        cyl(f, -0.05, 1.32, 0.08, 0.02, 0.09, 0.26, 6, beard, top=False); cyl(f, 0.05, 1.32, 0.08, 0.02, 0.09, 0.26, 6, beard, top=False)
        cyl(f, 0, 1.5, 0.05, 0.12, 0.13, 0.1, 8, beard)
    if hat == 'bowler':
        cyl(f, 0, 1.70, 0, 0.21, 0.21, 0.02, 12, (0.12, 0.12, 0.14)); cyl(f, 0, 1.71, 0, 0.13, 0.12, 0.14, 10, (0.12, 0.12, 0.14))
    elif hat == 'cap':
        cyl(f, 0, 1.69, 0, 0.14, 0.15, 0.12, 10, cap); box(f, 0, 1.70, 0.15, 0.22, 0.03, 0.14, 0, (0.08, 0.08, 0.1))
        box(f, 0, 1.79, 0.12, 0.08, 0.04, 0.02, 0, (0.95, 0.8, 0.3))
    elif hat == 'toque':
        cyl(f, 0, 1.68, 0, 0.13, 0.16, 0.24, 10, (0.97, 0.96, 0.93))
    elif hat == 'bonnet':
        sphere(f, 0, 1.64, -0.02, 0.15, (0.95, 0.92, 0.8), 10, 6, 1.0)
    elif hat == 'straw':
        cyl(f, 0, 1.70, 0, 0.3, 0.3, 0.02, 12, (0.92, 0.78, 0.35)); cyl(f, 0, 1.71, 0, 0.13, 0.11, 0.12, 10, (0.92, 0.78, 0.35))
    return f
FIG = [
    figure('npc_roulin', (0.12, 0.18, 0.40), 'cap', (0.12, 0.18, 0.40), beard=(0.55, 0.30, 0.12), cap=(0.12, 0.18, 0.40)),
    figure('npc_aug', (0.22, 0.42, 0.30), 'bonnet', (0.85, 0.55, 0.25), baby=True, dress=True),
    figure('npc_pan', (0.40, 0.30, 0.22), 'toque', (0.95, 0.93, 0.88), apron=True),
    figure('folk_1', (0.70, 0.18, 0.14), 'bowler', (0.2, 0.3, 0.5)),
    figure('folk_2', (0.78, 0.62, 0.22), 'straw', (0.6, 0.2, 0.15)),
    figure('folk_3', (0.30, 0.22, 0.45), 'bonnet', (0.9, 0.85, 0.7), dress=True),
    figure('folk_4', (0.15, 0.22, 0.42), 'bowler', (0.85, 0.75, 0.3)),
]

# ------------------------------------------------------------------ escena Blender + export
bpy.ops.wm.read_factory_settings(use_empty=True)
def to_obj(bld):
    me = bpy.data.meshes.new(bld.name)
    me.from_pydata(bld.v, [], bld.f); me.update()
    attr = me.color_attributes.new(name='Col', type='BYTE_COLOR', domain='CORNER')
    for poly in me.polygons:
        col = bld.c[poly.index] + (1.0,)
        for li in poly.loop_indices:
            attr.data[li].color = col
    me.color_attributes.active_color = attr
    ob = bpy.data.objects.new(bld.name, me); bpy.context.collection.objects.link(ob)
    return ob
for bld in [build, glow, street, churchwin] + FIG:
    to_obj(bld)
    print(bld.name, len(bld.f), 'faces')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'village.glb'), export_format='GLB', export_vertex_color='ACTIVE',
                          export_normals=True, export_texcoords=False, export_materials='NONE', export_apply=False, export_yup=True)

def r2(v): return round(v, 2)
layout = {
    'streets': [{'name': s['name'], 'hw': s['hw'], 'pts': s['pts']} for s in STREETS],
    'plaza': PLAZA, 'church': {**CHURCH, 'door': [r2(CHURCH_DOOR[0]), r2(CHURCH_DOOR[2])], 'steeple': [r2(v) for v in STEEPLE], 'front': fz},
    'village': VILLAGE,
    'houses': [[r2(h['x']), r2(h['z']), r2(h['hw']), r2(h['hd']), round(h['rot'], 3)] for h in houses],
    'lamps': lamps,
    'npc': {k: {'x': r2(SPECIAL[k]['door'][0]), 'z': r2(SPECIAL[k]['door'][2]), 'rot': round(SPECIAL[k]['rot'], 3)} for k in ('roulin', 'aug', 'pan')},
    'cafe': {'x': r2(Tc(0, 0, cafe['hd'] + 3)[0]), 'z': r2(Tc(0, 0, cafe['hd'] + 3)[2])},
    'bakery': {'x': r2(SPECIAL['pan']['door'][0]), 'z': r2(SPECIAL['pan']['door'][2])},
}
json.dump(layout, open(os.path.join(OUT, 'layout.json'), 'w'), separators=(',', ':'))
print('ok', os.path.getsize(os.path.join(OUT, 'village.glb')))
