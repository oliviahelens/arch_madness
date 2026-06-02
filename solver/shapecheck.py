"""Sound per-shape realizability oracle (optimized).

A region R's validity (integer area, no dangling) and smooth count depend only on
arcs of R's cells + cells adjacent to R's boundary. Structural facts used to make
the search fast:
  * A shape cell with an arc has its DISK in R and SLIVER outside, so BOTH its
    sliver-edges must face non-shape cells (else the sliver dangles back into R).
  * #disk(R) == #sliver(R); shape cells only contribute disks, so the slivers in
    R must come from exactly #disk boundary cells slivering inward.
  * Every boundary edge must be CUT (a sliver facing it, from either side).

can_realize_shape(shape, smooth) -> True | False | None(timeout).  Prune only on
False (sound).  Cached.
"""
import time
from itertools import product
from regions import DSU, piece_on_edge, DISK_EDGES
from perimeter import analyze, point_in_poly, rot

ARC = ("TL", "TR", "BL", "BR")
CORNER_XY = {"TL": (0, 0), "TR": (1, 0), "BL": (0, 1), "BR": (1, 1)}
EDGE_D = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}
OPP = {"T": "B", "B": "T", "L": "R", "R": "L"}


def normalize(shape):
    mr = min(r for r, c in shape); mc = min(c for r, c in shape)
    return frozenset((r - mr, c - mc) for r, c in shape)


def _point_to_piece(arcs, x, y, N):
    c = min(N - 1, max(0, int(x))); r = min(N - 1, max(0, int(y)))
    if (r, c) not in arcs:
        return (r, c, "W")
    ox, oy = CORNER_XY[arcs[(r, c)]]
    d = ((x - (c + ox)) ** 2 + (y - (r + oy)) ** 2) ** 0.5
    return (r, c, "D" if d < 1 else "S")


def _interior_point(face):
    cyc = face["cycle"]; h = cyc[0]
    if h.kind == "line":
        mid = ((h.origin[0] + h.dest[0]) / 2, (h.origin[1] + h.dest[1]) / 2)
        t = h.departure_dir()
    else:
        rP = (h.origin[0] - h.O[0], h.origin[1] - h.O[1])
        rr = rot(rP, h.sweep * 0.5); mid = (h.O[0] + rr[0], h.O[1] + rr[1])
        s = 1.0 if h.sweep > 0 else -1.0; t = (-s * rr[1], s * rr[0])
    for n in ((-t[1], t[0]), (t[1], -t[0])):
        p = (mid[0] + 1e-3 * n[0], mid[1] + 1e-3 * n[1])
        if point_in_poly(p, face["poly"]):
            return p
    return None


def _build_dsu(N, arcs):
    dsu = DSU(); pieces = []
    for r in range(N):
        for c in range(N):
            if (r, c) in arcs:
                pieces += [(r, c, "D"), (r, c, "S")]
            else:
                pieces.append((r, c, "W"))
    for p in pieces:
        dsu.find(p)
    for r in range(N):
        for c in range(N):
            if c + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "R"), piece_on_edge(arcs, r, c + 1, "L"))
            if r + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "B"), piece_on_edge(arcs, r + 1, c, "T"))
    return dsu, pieces


def _smooth_of_root(N, arcs, dsu, root):
    faces = analyze(N, arcs); outer = max(faces, key=lambda f: f["area"]); tot = 0
    for f in faces:
        if f is outer:
            continue
        ip = _interior_point(f)
        if ip is None:
            continue
        if dsu.find(_point_to_piece(arcs, ip[0], ip[1], N)) == root:
            tot += f["smooth"]
    return tot


_cache = {}


def can_realize_shape(cells_in, N, target_smooth, time_budget=2.0):
    """cells_in: region cells in ACTUAL NxN coordinates. Out-of-grid neighbours
    are the grid border (no cut / no sliver needed there)."""
    cells = sorted(cells_in)
    key = (frozenset(cells), N, target_smooth)
    if key in _cache:
        return _cache[key]
    cellset = set(cells)

    def in_grid(rc):
        return 0 <= rc[0] < N and 0 <= rc[1] < N

    # boundary dirs split into SEA (in-grid non-shape, need cut) and BORDER.
    bnd = {}        # cell -> boundary dirs (non-shape neighbour: sea or border)
    sea_dir = {}    # cell -> dirs whose neighbour is in-grid & non-shape
    for cell in cells:
        r, c = cell
        ds = []; sd = []
        for d, (dr, dc) in EDGE_D.items():
            nb = (r + dr, c + dc)
            if nb not in cellset:
                ds.append(d)
                if in_grid(nb):
                    sd.append(d)
        bnd[cell] = ds; sea_dir[cell] = sd

    def sliver_edges(K):
        de = DISK_EDGES[K]
        return [e for e in ("T", "B", "L", "R") if e not in de]

    # General SOUND search: assign arcs over shape cells + all edge/corner
    # neighbours (those can affect R's boundary geometry). A shape cell's disk
    # must stay in R; a shape cell MAY sliver toward another shape cell (the two
    # slivers form an internal bridge region) -- so no structural shortcut.
    ring = set()
    for (r, c) in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nb = (r + dr, c + dc)
                if in_grid(nb) and nb not in cellset:
                    ring.add(nb)
    assignable = list(cells) + sorted(ring)
    # boundary SEA edges that must be cut (label of shape cell != neighbour label)
    cut_pairs = set()
    for cell in cells:
        r, c = cell
        for d in sea_dir[cell]:
            dr, dc = EDGE_D[d]; nb = (r + dr, c + dc)
            cut_pairs.add(frozenset(((cell, d), (nb, OPP[d]))))

    start = time.time(); found = [False]; timed = [False]
    arcs = {}; assigned = set()

    def edge_cut(a, da, b, db):
        # is the edge between a (dir da) and b (dir db) cut? (sliver on either side)
        sa = arcs.get(a); sb = arcs.get(b)
        return (sa is not None and da not in DISK_EDGES[sa]) or \
               (sb is not None and db not in DISK_EDGES[sb])

    def cut_ok_local(cell):
        r, c = cell
        for d in sea_dir.get(cell, []):
            dr, dc = EDGE_D[d]; nb = (r + dr, c + dc)
            if nb in assigned and not edge_cut(cell, d, nb, OPP[d]):
                return False
        # if cell is a ring cell, also check its edges to shape cells that are cuts
        if cell not in cellset:
            for d, (dr, dc) in EDGE_D.items():
                nb = (r + dr, c + dc)
                if nb in cellset and nb in assigned and not edge_cut(cell, d, nb, OPP[d]):
                    return False
        return True

    def rec(i):
        if found[0]:
            return True
        if time.time() - start > time_budget:
            timed[0] = True; return True
        if i == len(assignable):
            if _validate_and_smooth(N, cells, cellset, dict(arcs)) == target_smooth:
                found[0] = True
            return found[0]
        cell = assignable[i]
        for v in (None,) + ARC:
            if v is not None:
                arcs[cell] = v
            assigned.add(cell)
            if cut_ok_local(cell):
                rec(i + 1)
            assigned.discard(cell); arcs.pop(cell, None)
            if found[0] or timed[0]:
                return found[0]
        return False

    def _validate_and_smooth(N, cells, cellset, arcs):
        dsu, pieces = _build_dsu(N, arcs)
        roots = set()
        for (r, c) in cells:
            lp = (r, c, "W") if (r, c) not in arcs else (r, c, "D")
            roots.add(dsu.find(lp))
        if len(roots) != 1:
            return None
        R = next(iter(roots))
        for r in range(N):
            for c in range(N):
                if (r, c) in cellset:
                    continue
                lp = (r, c, "W") if (r, c) not in arcs else (r, c, "D")
                if dsu.find(lp) == R:
                    return None
        Dc = Sc = 0
        for p in pieces:
            if dsu.find(p) == R:
                if p[2] == "D":
                    Dc += 1
                elif p[2] == "S":
                    Sc += 1
        if Dc != Sc:
            return None
        for (r, c) in cells:
            if (r, c) in arcs and dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
                return None
        return _smooth_of_root(N, arcs, dsu, R)

    rec(0)

    res = None if (timed[0] and not found[0]) else found[0]
    _cache[key] = res
    return res


if __name__ == "__main__":
    tests = [
        ({(0, 1), (0, 2), (1, 2)}, 4, 3, "L-tromino smooth3 @border (example)"),
        ({(2, 2), (2, 3), (3, 2), (3, 3)}, 4, 6, "2x2 smooth6 @corner (example=24)"),
        ({(1, 0), (1, 1), (2, 0), (2, 1)}, 4, 2, "2x2 smooth2 @edge (example=8)"),
        ({(3, 3), (3, 4), (3, 5), (4, 3), (4, 4), (4, 5), (5, 3), (5, 4), (5, 5)}, 9, 3,
         "3x3 smooth3 interior (clue27 size9)"),
        ({(4, 3), (4, 4), (4, 5)}, 9, 7, "I-tromino smooth7 interior (clue21)"),
        ({(4, 3), (4, 4), (4, 5)}, 9, 9, "I-tromino smooth9 interior (likely False)"),
        ({(4, 3), (4, 4), (4, 5)}, 9, 3, "I-tromino smooth3 interior (clue9)"),
    ]
    for sh, N, s, desc in tests:
        t = time.time(); r = can_realize_shape(sh, N, s, time_budget=6.0)
        print(f"  {desc}: realizable={r}  ({time.time()-t:.2f}s)")
