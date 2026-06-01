"""Backtracking solver with frontier-closure pruning.

Cells are assigned in row-major order. As soon as a region can no longer grow
(all its pieces are sealed off from unassigned cells), it is validated:
  - integer area (disk count == sliver count)
  - no dangling arc (an arc whose two pieces ended up in the same region)
  - any clue in it: area must divide the clue (and smooth = clue/area >= 1)
Dead branches die early. Full smooth-score is verified at the leaf via the
validated engine (solver.score_regions).
"""

import sys
import time
from collections import defaultdict

from regions import DSU, piece_on_edge
from perimeter import analyze
from solver import score_regions, readout, clues_ok, interior_point
import input as data

CORNER_XY = {"TL": (0, 0), "TR": (1, 0), "BL": (0, 1), "BR": (1, 1)}


def point_to_piece(N, arcs, x, y):
    c = min(N - 1, max(0, int(x)))
    r = min(N - 1, max(0, int(y)))
    if (r, c) not in arcs:
        return (r, c, "W")
    ox, oy = CORNER_XY[arcs[(r, c)]]
    d = ((x - (c + ox)) ** 2 + (y - (r + oy)) ** 2) ** 0.5
    return (r, c, "D" if d < 1 else "S")


def smooth_by_root(N, arcs, dsu):
    """Smooth-piece count per region root, from the current (partial) arrangement."""
    faces = analyze(N, arcs)
    outer = max(faces, key=lambda f: f["area"])
    tot = defaultdict(int)
    for f in faces:
        if f is outer:
            continue
        ip = interior_point(f)
        if ip is None:
            continue
        tot[dsu.find(point_to_piece(N, arcs, ip[0], ip[1]))] += f["smooth"]
    return tot

DIRS = (None, "TL", "TR", "BL", "BR")
EDGE_NB = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}


def partial_components(N, arcs, assigned):
    dsu = DSU()
    pieces = []
    for (r, c) in assigned:
        if (r, c) in arcs:
            pieces.append((r, c, "D"))
            pieces.append((r, c, "S"))
        else:
            pieces.append((r, c, "W"))
    for p in pieces:
        dsu.find(p)
    for (r, c) in assigned:
        if (r, c + 1) in assigned:
            dsu.union(piece_on_edge(arcs, r, c, "R"), piece_on_edge(arcs, r, c + 1, "L"))
        if (r + 1, c) in assigned:
            dsu.union(piece_on_edge(arcs, r, c, "B"), piece_on_edge(arcs, r + 1, c, "T"))
    comp = defaultdict(list)
    for p in pieces:
        comp[dsu.find(p)].append(p)
    return dsu, comp


def is_open(N, arcs, assigned, p):
    r, c, _ = p
    for d, (dr, dc) in EDGE_NB.items():
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < N and (nr, nc) not in assigned:
            if piece_on_edge(arcs, r, c, d) == p:
                return True
    return False


def closure_ok(N, arcs, assigned, clues):
    dsu, comp = partial_components(N, arcs, assigned)
    info = {}        # root -> (full, D, S)
    closed = {}      # root -> bool
    for root, ps in comp.items():
        info[root] = (sum(p[2] == "W" for p in ps),
                      sum(p[2] == "D" for p in ps),
                      sum(p[2] == "S" for p in ps))
        closed[root] = not any(is_open(N, arcs, assigned, p) for p in ps)

    # Clue value(s) attached to each region (by label piece).
    root_clue = {}
    for (r, c), val in clues.items():
        if (r, c) in assigned:
            lp = (r, c, "W") if (r, c) not in arcs else (r, c, "D")
            root = dsu.find(lp)
            if root in root_clue and root_clue[root] != val:
                return False  # two distinct clues in one region
            root_clue[root] = val

    # Open-region lower bound: committed labeled cells (full+disk) <= clue,
    # because final score = smooth*area >= area >= committed cells.
    for root, val in root_clue.items():
        full, D, S = info[root]
        if full + D > val:
            return False

    # Closed-region exact checks.
    for root, ps in comp.items():
        if not closed[root]:
            continue
        full, D, S = info[root]
        if D != S:
            return False  # non-integer area
        for (r, c) in {(p[0], p[1]) for p in ps if p[2] in ("D", "S")}:
            if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
                return False  # dangling arc

    clue_closed = {root: val for root, val in root_clue.items() if closed[root]}
    if clue_closed:
        sm = smooth_by_root(N, arcs, dsu)
        for root, val in clue_closed.items():
            full, D, S = info[root]
            if sm.get(root, 0) * (full + D) != val:
                return False  # exact score mismatch
    return True


def solve(N, clues, green, time_limit=120, want=None):
    order = [(r, c) for r in range(N) for c in range(N)]
    assign = {}
    assigned = set()
    arcs = {}
    sols = []
    start = time.time()
    stats = {"nodes": 0, "timeout": False}

    def rec(i):
        if stats["timeout"] or time.time() - start > time_limit:
            stats["timeout"] = True
            return
        if i == len(order):
            res = score_regions(N, dict(arcs))
            if res:
                cs, info = res
                if clues_ok(cs, clues):
                    ans = readout(N, cs)
                    sols.append((dict(arcs), ans))
                    print(f"  SOLUTION answer={ans}")
            return
        r, c = order[i]
        domain = (None,) if (r, c) in green else DIRS
        for v in domain:
            stats["nodes"] += 1
            assign[(r, c)] = v
            assigned.add((r, c))
            if v is not None:
                arcs[(r, c)] = v
            if closure_ok(N, arcs, assigned, clues):
                rec(i + 1)
                if want is not None and sols and sols[-1][1] == want:
                    return
            assigned.discard((r, c))
            assign.pop((r, c), None)
            arcs.pop((r, c), None)

    rec(0)
    return sols, stats


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "example"
    p = data.EXAMPLE if which == "example" else data.PUZZLE
    tl = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    sols, stats = solve(p["N"], p["clues"], p["green"], time_limit=tl,
                        want=p.get("answer"))
    print(f"nodes={stats['nodes']} timeout={stats['timeout']} solutions={len(sols)}")
    for arcs, ans in sols[:5]:
        print("answer", ans, "arcs", arcs)
