"""Scoring integration + search. Validate on the 4x4 (must give 18928)."""

import sys
import time
import itertools
from collections import defaultdict

from regions import build_regions
from perimeter import analyze, point_in_poly, rot
import input as data

ARC_DIRS = ("TL", "TR", "BL", "BR")
CORNER_XY = {"TL": (0, 0), "TR": (1, 0), "BL": (0, 1), "BR": (1, 1)}


def map_point_to_root(N, arcs, root_of, x, y):
    c = min(N - 1, max(0, int(x)))
    r = min(N - 1, max(0, int(y)))
    if (r, c) not in arcs:
        return root_of.get((r, c, "W"))
    ox, oy = CORNER_XY[arcs[(r, c)]]
    Ox, Oy = c + ox, r + oy
    d = ((x - Ox) ** 2 + (y - Oy) ** 2) ** 0.5
    return root_of.get((r, c, "D" if d < 1 else "S"))


def interior_point(face):
    cyc = face["cycle"]
    h = cyc[0]
    if h.kind == "line":
        mid = ((h.origin[0] + h.dest[0]) / 2, (h.origin[1] + h.dest[1]) / 2)
        t = h.departure_dir()
    else:
        rP = (h.origin[0] - h.O[0], h.origin[1] - h.O[1])
        rr = rot(rP, h.sweep * 0.5)
        mid = (h.O[0] + rr[0], h.O[1] + rr[1])
        s = 1.0 if h.sweep > 0 else -1.0
        t = (-s * rr[1], s * rr[0])
    for n in ((-t[1], t[0]), (t[1], -t[0])):
        p = (mid[0] + 1e-3 * n[0], mid[1] + 1e-3 * n[1])
        if point_in_poly(p, face["poly"]):
            return p
    return None


def score_regions(N, arcs):
    """Return (cell_score grid, per-root info) or None if invalid geometry."""
    reg = build_regions(N, arcs)
    if not reg["ok"]:
        return None
    root_of = reg["root_of"]
    area = reg["region_area"]
    faces = analyze(N, arcs)
    # The unbounded/outer face encloses the whole grid (polygon area ~ N^2);
    # exclude it so its boundary isn't mis-attributed to a real region.
    outer = max(faces, key=lambda f: f["area"])
    smooth = defaultdict(int)
    for f in faces:
        if f is outer:
            continue
        ip = interior_point(f)
        if ip is None:
            continue
        root = map_point_to_root(N, arcs, root_of, ip[0], ip[1])
        if root is None:
            continue
        smooth[root] += f["smooth"]
    label = reg["label_root"]
    cell_score = {}
    for (r, c), root in label.items():
        if root not in smooth:
            return None  # a labeled region got no boundary -> inconsistency
        cell_score[(r, c)] = area[root] * smooth[root]
    return cell_score, {root: (area[root], smooth[root]) for root in area}


def readout(N, cell_score):
    rows = [sum(cell_score[(r, c)] for c in range(N)) for r in range(N)]
    cols = [sum(cell_score[(r, c)] for r in range(N)) for c in range(N)]
    return sum(s * s for s in rows) + sum(s * s for s in cols)


def clues_ok(cell_score, clues):
    return all(cell_score.get(k) == v for k, v in clues.items())


def solve(N, clues, green, max_arcs=14, time_limit=180, want_answer=None):
    free = [(r, c) for r in range(N) for c in range(N) if (r, c) not in green]
    start = time.time()
    tried = 0
    found = []
    for k in range(0, max_arcs + 1):
        for subset in itertools.combinations(free, k):
            for dirs in itertools.product(ARC_DIRS, repeat=k):
                if time.time() - start > time_limit:
                    print(f"  [time limit; tried {tried}]")
                    return found
                tried += 1
                arcs = {cell: d for cell, d in zip(subset, dirs)}
                res = score_regions(N, arcs)
                if res is None:
                    continue
                cell_score, info = res
                if not clues_ok(cell_score, clues):
                    continue
                ans = readout(N, cell_score)
                found.append((arcs, ans, info))
                print(f"  SOLUTION k={k} answer={ans}")
                if want_answer is not None and ans == want_answer:
                    return found
        if found:
            return found
    return found


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "example"
    if which == "example":
        N = data.EXAMPLE["N"]
        sols = solve(N, data.EXAMPLE["clues"], data.EXAMPLE["green"],
                     max_arcs=14, time_limit=240, want_answer=18928)
        print("example solutions found:", len(sols))
        for arcs, ans, info in sols[:3]:
            print("  answer", ans, "arcs", arcs)
