"""Geometry: trace region boundaries and count smooth (C^1) perimeter pieces.

Coordinates: point = (x, y), x = column (0..N), y = row (0..N), y downward.
Cell (r,c) corners: TL=(c,r) TR=(c+1,r) BL=(c,r+1) BR=(c+1,r+1).

Arrangement edges:
  - the outer border (unit axis-aligned segments), always present
  - each placed arc (quarter circle radius 1 between two diagonal corners,
    centered at the third/"center" corner)
Interior grid lines are NOT edges. The bounded faces are exactly the regions.

A key fact: a quarter-arc is TANGENT to the two cell edges at its endpoints,
so an arc meeting a collinear straight border (or another tangent arc) is a
smooth join; a 90-degree straight/straight meeting is a break.
"""

import math

EPS = 1e-7
SAMPLE_S = 1e-4

CENTER_CORNER = {  # arc center -> (corner offset) in (dx,dy) from cell TL
    "TL": (0, 0), "TR": (1, 0), "BL": (0, 1), "BR": (1, 1),
}


def corners(r, c):
    return {
        "TL": (c, r), "TR": (c + 1, r), "BL": (c, r + 1), "BR": (c + 1, r + 1),
    }


def arc_geometry(r, c, center):
    """Return (O, P, Q): center point and the two diagonal endpoints."""
    cn = corners(r, c)
    O = cn[center]
    # endpoints are the two corners adjacent to O (distance 1) -> the diagonal pair
    others = [k for k in ("TL", "TR", "BL", "BR") if k != center]
    # the corner diagonally opposite O is the one differing in both coords; exclude it
    ox, oy = O
    endpoints = [cn[k] for k in others if abs(cn[k][0] - ox) + abs(cn[k][1] - oy) == 1]
    P, Q = endpoints
    return O, P, Q


def rot(v, ang):
    x, y = v
    ca, sa = math.cos(ang), math.sin(ang)
    return (x * ca - y * sa, x * sa + y * ca)


class HE:
    """Directed half-edge."""
    __slots__ = ("origin", "dest", "kind", "O", "sweep", "twin", "idx")

    def __init__(self, origin, dest, kind, O=None, sweep=0.0):
        self.origin = origin
        self.dest = dest
        self.kind = kind  # 'line' or 'arc'
        self.O = O        # arc center (for arc)
        self.sweep = sweep  # signed sweep angle origin->dest (for arc)
        self.twin = None
        self.idx = None

    def departure_dir(self):
        if self.kind == "line":
            dx = self.dest[0] - self.origin[0]
            dy = self.dest[1] - self.origin[1]
            n = math.hypot(dx, dy)
            return (dx / n, dy / n)
        # arc: tangent at origin in travel direction
        rP = (self.origin[0] - self.O[0], self.origin[1] - self.O[1])
        s = 1.0 if self.sweep > 0 else -1.0
        return (-s * rP[1], s * rP[0])  # rotate radial by +/-90

    def arrival_dir(self):
        if self.kind == "line":
            return self.departure_dir()
        rQ = (self.dest[0] - self.O[0], self.dest[1] - self.O[1])
        s = 1.0 if self.sweep > 0 else -1.0
        return (-s * rQ[1], s * rQ[0])

    def sample_angle(self):
        """Chord angle from origin to a point a tiny step along the edge
        (captures curvature for tie-breaking in rotational order)."""
        if self.kind == "line":
            d = self.departure_dir()
            px, py = self.origin[0] + SAMPLE_S * d[0], self.origin[1] + SAMPLE_S * d[1]
        else:
            rP = (self.origin[0] - self.O[0], self.origin[1] - self.O[1])
            s = 1.0 if self.sweep > 0 else -1.0
            rr = rot(rP, s * SAMPLE_S)
            px, py = self.O[0] + rr[0], self.O[1] + rr[1]
        return math.atan2(py - self.origin[1], px - self.origin[0])

    def polyline(self, n=24):
        if self.kind == "line":
            return [self.origin, self.dest]
        pts = []
        rP = (self.origin[0] - self.O[0], self.origin[1] - self.O[1])
        for k in range(n + 1):
            rr = rot(rP, self.sweep * k / n)
            pts.append((self.O[0] + rr[0], self.O[1] + rr[1]))
        return pts


def _sweep_sign(O, P, Q):
    aP = math.atan2(P[1] - O[1], P[0] - O[0])
    aQ = math.atan2(Q[1] - O[1], Q[0] - O[0])
    d = aQ - aP
    while d > math.pi:
        d -= 2 * math.pi
    while d <= -math.pi:
        d += 2 * math.pi
    return d  # ~ +/- pi/2


def build_halfedges(N, arcs):
    hes = []

    def add_pair(a, b, kind, O=None, sweepAB=0.0):
        h1 = HE(a, b, kind, O, sweepAB)
        h2 = HE(b, a, kind, O, -sweepAB)
        h1.twin, h2.twin = h2, h1
        hes.append(h1)
        hes.append(h2)

    # border unit segments (clockwise rectangle of the NxN square)
    for c in range(N):       # top
        add_pair((c, 0), (c + 1, 0), "line")
    for r in range(N):       # right
        add_pair((N, r), (N, r + 1), "line")
    for c in range(N):       # bottom
        add_pair((c + 1, N), (c, N), "line")
    for r in range(N):       # left
        add_pair((0, r + 1), (0, r), "line")

    # arcs
    for (r, c), center in arcs.items():
        O, P, Q = arc_geometry(r, c, center)
        sw = _sweep_sign(O, P, Q)
        add_pair(P, Q, "arc", O, sw)

    return hes


def trace_faces(hes):
    # group outgoing half-edges by origin, sorted CCW by sample angle
    from collections import defaultdict
    out = defaultdict(list)
    for h in hes:
        out[h.origin].append(h)
    for v in out:
        out[v].sort(key=lambda h: h.sample_angle())
        for i, h in enumerate(out[v]):
            h.idx = i

    def next_he(h):
        w = h.dest
        lst = out[w]
        twin = h.twin
        i = twin.idx
        return lst[(i - 1) % len(lst)]

    faces = []
    visited = set()
    for h in hes:
        if id(h) in visited:
            continue
        cycle = []
        cur = h
        while id(cur) not in visited:
            visited.add(id(cur))
            cycle.append(cur)
            cur = next_he(cur)
        faces.append(cycle)
    return faces


def polygon(cycle):
    pts = []
    for h in cycle:
        seg = h.polyline()
        pts.extend(seg[:-1])
    return pts


def signed_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def count_smooth(cycle):
    """Number of maximal C^1 pieces around this face boundary."""
    m = len(cycle)
    breaks = 0
    for i in range(m):
        h1 = cycle[i]
        h2 = cycle[(i + 1) % m]
        a = h1.arrival_dir()
        d = h2.departure_dir()
        if a[0] * d[0] + a[1] * d[1] < 1 - 1e-6:  # directions differ -> corner
            breaks += 1
    return breaks if breaks > 0 else 1


def point_in_poly(pt, pts):
    x, y = pt
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def analyze(N, arcs):
    """Return list of faces: each {smooth, polygon, area_signed}. Outer face
    is the one with no cell center inside (handled by caller)."""
    hes = build_halfedges(N, arcs)
    faces = trace_faces(hes)
    out = []
    for cyc in faces:
        pts = polygon(cyc)
        out.append({
            "smooth": count_smooth(cyc),
            "poly": pts,
            "area": abs(signed_area(pts)),
            "cycle": cyc,
        })
    return out
