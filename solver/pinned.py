"""Pinned-area region-growing solver.

From Sum(areas)=81 + divisor/parity analysis, every region's (area,smooth) is
forced:
    clue 9 ->(3,3)  15->(3,5)  21->(3,7)  25->(5,5)  27->(3,9)
    clue 35->(5,7)  45->(5,9)  63->(7,9)  288->(12,24)
We CAP each clue region's labelled-cell count at its target area, so growth is
bounded the instant it would overshoot -- the exact-score prune then fires at
seal. Regions tile the grid exactly (no unclued region).
"""
import sys, time, random
from collections import defaultdict
from regions import DSU, piece_on_edge
from backtrack import partial_components, is_open, smooth_by_root
from solver import score_regions, readout, clues_ok
import input as data

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))

AREA = {9: 3, 15: 3, 21: 3, 25: 5, 27: 3, 35: 5, 45: 5, 63: 7, 288: 12}


def closure_capped(N, arcs, assigned, clues, area_cap):
    dsu, comp = partial_components(N, arcs, assigned)
    info = {}
    closed = {}
    for root, ps in comp.items():
        info[root] = (sum(p[2] == "W" for p in ps),
                      sum(p[2] == "D" for p in ps),
                      sum(p[2] == "S" for p in ps))
        closed[root] = not any(is_open(N, arcs, assigned, p) for p in ps)

    root_clue = {}
    for (r, c), val in clues.items():
        if (r, c) in assigned:
            lp = (r, c, "W") if (r, c) not in arcs else (r, c, "D")
            root = dsu.find(lp)
            if root in root_clue and root_clue[root] != val:
                return False
            root_clue[root] = val

    # area cap: labelled cells (full+disk) must not exceed the region target.
    for root, val in root_clue.items():
        full, D, S = info[root]
        if full + D > area_cap[val]:
            return False

    for root, ps in comp.items():
        if not closed[root]:
            continue
        full, D, S = info[root]
        if D != S:
            return False
        for (r, c) in {(p[0], p[1]) for p in ps if p[2] in ("D", "S")}:
            if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
                return False
        # A closed region with no clue must still tile cleanly; its area is
        # whatever it is (unclued regions allowed in principle, but our model
        # says none -- so a closed unclued region is only ok if it's the leftover
        # handled at the leaf). Allow it here; leaf check is exact.

    clue_closed = {root: val for root, val in root_clue.items() if closed[root]}
    if clue_closed:
        sm = smooth_by_root(N, arcs, dsu)
        for root, val in clue_closed.items():
            full, D, S = info[root]
            if sm.get(root, 0) * (full + D) != val:
                return False
    return True


def label_piece(cell, arcs):
    return (cell[0], cell[1], "W") if cell not in arcs else (cell[0], cell[1], "D")


def focus_frontier(N, arcs, assigned, cluecell):
    dsu, comp = partial_components(N, arcs, assigned)
    root = dsu.find(label_piece(cluecell, arcs))
    EDGE_NB = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}
    seen = set(); frontier = []
    for p in comp[root]:
        r, c, _ = p
        for d, (dr, dc) in EDGE_NB.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < N and 0 <= nc < N and (nr, nc) not in assigned:
                if piece_on_edge(arcs, r, c, d) == p and (nr, nc) not in seen:
                    seen.add((nr, nc)); frontier.append((nr, nc))
    return frontier if frontier else None


def solve(N, clues, green, area_cap, queue_order, time_limit=300, seed=0, want=None,
          progress=True):
    allcells = [(r, c) for r in range(N) for c in range(N)]
    rng = random.Random(seed)
    queue = queue_order
    assigned = set(); arcs = {}
    sols = []
    start = time.time()
    st = {"nodes": 0, "best": 0, "timeout": False}

    def up():
        if time.time() - start > time_limit:
            st["timeout"] = True; return True
        return False

    def try_assign(cell, v, cont):
        st["nodes"] += 1
        assigned.add(cell)
        if v is not None: arcs[cell] = v
        r = False
        if closure_capped(N, arcs, assigned, clues, area_cap):
            r = cont()
        assigned.discard(cell); arcs.pop(cell, None)
        return r

    def grow(qi, cell0):
        if st["timeout"] or up(): return True
        if cell0 not in assigned:
            dom = (None,) if cell0 in green else (None, "TL", "TR", "BL", "BR")
            dom = list(dom); rng.shuffle(dom)
            for v in dom:
                if try_assign(cell0, v, lambda: grow(qi, cell0)): return True
            return False
        front = focus_frontier(N, arcs, assigned, cell0)
        if front is None:
            return nextc(qi + 1)
        cell = front[0]
        dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
        dom = list(dom); rng.shuffle(dom)
        for v in dom:
            if try_assign(cell, v, lambda: grow(qi, cell0)): return True
        return False

    def nextc(qi):
        if qi > st["best"]:
            st["best"] = qi
            if progress:
                cl = clues[queue[qi-1]] if qi-1 < len(queue) else "?"
                print(f"  seed{seed}: sealed {qi}/{len(queue)} regions "
                      f"(last clue {cl}) nodes={st['nodes']} "
                      f"{st['nodes']/(time.time()-start+1e-9):.0f}/s", flush=True)
        if qi == len(queue):
            return finish()
        return grow(qi, queue[qi])

    def finish():
        rem = [c for c in allcells if c not in assigned]
        def rec(i):
            if st["timeout"] or up(): return True
            if i == len(rem):
                res = score_regions(N, dict(arcs))
                if res and clues_ok(res[0], clues):
                    ans = readout(N, res[0])
                    sols.append((dict(arcs), ans))
                    print(f"  *** SOLUTION seed{seed} answer={ans} ***", flush=True)
                    return want is None or ans == want
                return False
            cell = rem[i]
            dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
            dom = list(dom); rng.shuffle(dom)
            for v in dom:
                if try_assign(cell, v, lambda: rec(i + 1)): return True
            return False
        return rec(0)

    nextc(0)
    return sols, st


def build_queue(clues, green, N, rng):
    NB2 = ((0, 1), (1, 0), (0, -1), (-1, 0))
    def key(cell):
        r, c = cell
        edge = min(r, N-1-r) + min(c, N-1-c)
        gn = sum((r+dr, c+dc) in green for dr, dc in NB2)
        # smallest area first, near border, near greens, defer 288
        return (AREA[clues[cell]], edge, -gn, rng.random())
    return sorted(clues, key=key)


if __name__ == "__main__":
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    p = data.PUZZLE; N = p["N"]; clues = p["clues"]; green = p["green"]
    rng = random.Random(seed)
    area_cap = {v: AREA[v] for v in set(clues.values())}
    queue = build_queue(clues, green, N, rng)
    print("queue (clue values):", [clues[c] for c in queue], flush=True)
    sols, st = solve(N, clues, green, area_cap, queue, time_limit=tl, seed=seed)
    print(f"seed={seed} nodes={st['nodes']} best={st['best']}/{len(queue)} "
          f"timeout={st['timeout']} sols={len(sols)}")
    for arcs, ans in sols[:1]:
        print("ANSWER", ans); print("ARCS", arcs)
