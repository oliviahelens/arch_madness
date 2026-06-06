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
AUTOSAVE = [False]
_CACHE_FILE = __file__.rsplit("/", 1)[0] + "/shapecache.pkl"


def load_cache():
    import pickle, os
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "rb") as f:
                _cache.update(pickle.load(f))
        except Exception:
            pass
    return len(_cache)


def save_cache():
    import pickle
    with open(_CACHE_FILE, "wb") as f:
        pickle.dump(_cache, f)
    return len(_cache)


def can_realize_shape(cells_in, N, target_smooth, time_budget=2.0, green=frozenset()):
    """cells_in: region cells in ACTUAL NxN coordinates. Out-of-grid neighbours
    are the grid border (no cut / no sliver needed there). green cells in the
    region are forced WHOLE (no arc)."""
    cells0 = sorted(cells_in)
    green0 = frozenset(c for c in cells0 if c in green)
    key = (frozenset(cells0), N, target_smooth, green0)
    if key in _cache:
        return _cache[key]
    # --- localize to a small square window (region validity+smooth are local) ---
    r0 = min(r for r, c in cells0); r1 = max(r for r, c in cells0)
    c0 = min(c for r, c in cells0); c1 = max(c for r, c in cells0)
    h = r1 - r0 + 1; w = c1 - c0 + 1
    top = 0 if r0 == 0 else 1; bot = 0 if r1 == N - 1 else 1
    left = 0 if c0 == 0 else 1; right = 0 if c1 == N - 1 else 1
    L = max(h + top + bot, w + left + right)
    row_off = 0 if r0 == 0 else (L - h if r1 == N - 1 else 1)
    col_off = 0 if c0 == 0 else (L - w if c1 == N - 1 else 1)

    def remap(rc):
        return (rc[0] - r0 + row_off, rc[1] - c0 + col_off)
    cells = [remap(c) for c in cells0]
    greenc = frozenset(remap(c) for c in green0)
    N = L
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

    start = time.time(); found = [False]; timed = [False]

    def try_full(shape_arcs):
        """shape_arcs: dict cell->arc|None for every region cell (ALL options).
        R's boundary (hence its smooth) depends ONLY on R's cells' arcs plus the
        sea cells that sliver into R's LABEL-edges. Every sea edge where R shows
        its label MUST be cut by an inward sea sliver (else R merges with sea);
        those inward slivers are exactly #sliver(R), which must == #disk(R)=D.
        Enumerating those sea cells' arcs is COMPLETE for R's smooth -> a clean
        exhaustion is a sound False."""
        if found[0] or time.time() - start > time_budget:
            if not found[0]:
                timed[0] = True
            return
        D = sum(1 for cell in cells if shape_arcs[cell] is not None)
        # sea cells forced to sliver into R, with the dirs (their view) they must cover
        need = {}                    # sea cell -> set of sliver dirs it must show
        for cell in cells:
            K = shape_arcs[cell]
            label = set(DISK_EDGES[K]) if K is not None else {"T", "B", "L", "R"}
            for e in sea_dir[cell]:
                if e in label:       # R shows its label across this sea edge
                    dr, dc = EDGE_D[e]; oc = (cell[0] + dr, cell[1] + dc)
                    need.setdefault(oc, set()).add(OPP[e])
        if len(need) != D:           # integer area: #sliver(R)==#disk(R)
            return
        opts = []
        for oc, dirs in need.items():
            allow = [K for K in ARC if dirs <= set(sliver_edges(K))]
            if not allow:
                return
            opts.append((oc, allow))
        base = {c: a for c, a in shape_arcs.items() if a is not None}
        cells_o = [oc for oc, _ in opts]; allows = [al for _, al in opts]
        for choice in (product(*allows) if opts else [()]):
            a = dict(base)
            for oc, K in zip(cells_o, choice):
                a[oc] = K
            if _validate_and_smooth(N, cells, cellset, a) == target_smooth:
                found[0] = True; return
            if time.time() - start > time_budget:
                timed[0] = True; return

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

    cellopts = [((None,) if cell in greenc else ((None,) + ARC)) for cell in cells]
    for combo in product(*cellopts):
        if found[0] or time.time() - start > time_budget:
            if not found[0]:
                timed[0] = True
            break
        try_full(dict(zip(cells, combo)))

    res = None if (timed[0] and not found[0]) else found[0]
    _cache[key] = res
    if AUTOSAVE[0] and len(_cache) % 50 == 0:
        try:
            save_cache()
        except Exception:
            pass
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
