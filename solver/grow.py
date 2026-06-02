"""Compact region-growing backtracker.

Variable ordering: always assign the unassigned cell with the most already-
assigned orthogonal neighbours (fills concavities so regions SEAL and get
exact-score-checked early). Random tie-break (seeded) for parallel restarts.

Prunes (all sound):
  - closure_ok from backtrack.py: integer area + no-dangling + clue divisibility
    + exact smooth-score on every CLOSED clue region.
  - area budget: sum of CLOSED region areas <= N*N (total area is exactly N*N).
"""
import os, sys, time, random
from collections import defaultdict
from regions import DSU, piece_on_edge
from backtrack import closure_ok, partial_components
from solver import score_regions, readout, clues_ok
import input as data

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))


def closed_area_sum(N, arcs, assigned):
    """Sum of areas of regions all of whose pieces are sealed from unassigned."""
    dsu, comp = partial_components(N, arcs, assigned)
    from backtrack import is_open
    tot = 0
    for root, ps in comp.items():
        if any(is_open(N, arcs, assigned, p) for p in ps):
            continue
        D = sum(p[2] == "D" for p in ps)
        W = sum(p[2] == "W" for p in ps)
        S = sum(p[2] == "S" for p in ps)
        if D == S:
            tot += W + D
    return tot


def solve(N, clues, green, time_limit=120, seed=0, want=None, progress=False):
    allcells = [(r, c) for r in range(N) for c in range(N)]
    cluecells = set(clues)
    rng = random.Random(seed)
    jitter = {cell: rng.random() for cell in allcells}

    assigned = set()
    arcs = {}
    nbrcnt = {cell: 0 for cell in allcells}   # incremental assigned-neighbour count
    sols = []
    start = time.time()
    stats = {"nodes": 0, "maxd": 0, "timeout": False}

    def pick():
        best = None; bk = None
        for cell in allcells:
            if cell in assigned:
                continue
            k = nbrcnt[cell]
            key = (k, cell in cluecells, jitter[cell])
            if bk is None or key > bk:
                bk = key; best = cell
        return best

    def add(cell):
        assigned.add(cell)
        r, c = cell
        for dr, dc in NB:
            nb = (r + dr, c + dc)
            if nb in nbrcnt:
                nbrcnt[nb] += 1

    def rem(cell):
        assigned.discard(cell)
        r, c = cell
        for dr, dc in NB:
            nb = (r + dr, c + dc)
            if nb in nbrcnt:
                nbrcnt[nb] -= 1

    def rec(depth):
        if stats["timeout"] or time.time() - start > time_limit:
            stats["timeout"] = True
            return True
        if depth > stats["maxd"]:
            stats["maxd"] = depth
            if progress and depth % 5 == 0:
                print(f"  seed{seed} depth {depth} nodes {stats['nodes']} "
                      f"{stats['nodes']/(time.time()-start):.0f}/s", flush=True)
        if depth == len(allcells):
            res = score_regions(N, dict(arcs))
            if res and clues_ok(res[0], clues):
                ans = readout(N, res[0])
                sols.append((dict(arcs), ans))
                print(f"  *** SOLUTION seed{seed} answer={ans} ***", flush=True)
                return want is None or ans == want
            return False
        cell = pick()
        dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
        # randomize value order per seed
        dom = list(dom); rng.shuffle(dom)
        for v in dom:
            stats["nodes"] += 1
            add(cell)
            if v is not None:
                arcs[cell] = v
            ok = closure_ok(N, arcs, assigned, clues)
            if ok:
                if rec(depth + 1):
                    rem(cell); arcs.pop(cell, None); return True
            rem(cell); arcs.pop(cell, None)
        return False

    rec(0)
    return sols, stats


if __name__ == "__main__":
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    p = data.PUZZLE
    sols, stats = solve(p["N"], p["clues"], p["green"], time_limit=tl, seed=seed, progress=True)
    print(f"seed={seed} nodes={stats['nodes']} maxd={stats['maxd']} "
          f"timeout={stats['timeout']} sols={len(sols)}")
    for arcs, ans in sols[:3]:
        print("answer", ans)
        print("arcs", arcs)
