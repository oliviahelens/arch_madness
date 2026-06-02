"""Compact growth + pinned area-cap prune.

Variable order: cell with most assigned orthogonal neighbours (compact blob;
regions seal early against border + already-placed cells).
Prune: closure_capped -- every clue region's labelled cells capped at its
forced target area (fires on OPEN regions instantly), plus integer-area,
no-dangling, and exact smooth-score at seal.
"""
import sys, time, random
from pinned import closure_capped, AREA
from solver import score_regions, readout, clues_ok
import input as data

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))


def solve(N, clues, green, time_limit=300, seed=0, want=None, progress=True):
    allcells = [(r, c) for r in range(N) for c in range(N)]
    cluecells = set(clues)
    area_cap = {v: AREA[v] for v in set(clues.values())}
    rng = random.Random(seed)
    jitter = {cell: rng.random() for cell in allcells}
    assigned = set(); arcs = {}
    nbr = {cell: 0 for cell in allcells}
    sols = []; start = time.time()
    st = {"nodes": 0, "maxd": 0, "timeout": False}

    def pick():
        best = None; bk = None
        for cell in allcells:
            if cell in assigned: continue
            k = (nbr[cell], cell in cluecells, jitter[cell])
            if bk is None or k > bk:
                bk = k; best = cell
        return best

    def add(cell):
        assigned.add(cell)
        r, c = cell
        for dr, dc in NB:
            nb = (r+dr, c+dc)
            if nb in nbr: nbr[nb] += 1

    def rem(cell):
        assigned.discard(cell)
        r, c = cell
        for dr, dc in NB:
            nb = (r+dr, c+dc)
            if nb in nbr: nbr[nb] -= 1

    def rec(depth):
        if st["timeout"] or time.time() - start > time_limit:
            st["timeout"] = True; return True
        if depth > st["maxd"]:
            st["maxd"] = depth
            if progress and depth % 5 == 0:
                print(f"  seed{seed} depth {depth} nodes {st['nodes']} "
                      f"{st['nodes']/(time.time()-start+1e-9):.0f}/s", flush=True)
        if depth == len(allcells):
            res = score_regions(N, dict(arcs))
            if res and clues_ok(res[0], clues):
                ans = readout(N, res[0]); sols.append((dict(arcs), ans))
                print(f"  *** SOLUTION seed{seed} answer={ans} ***", flush=True)
                return want is None or ans == want
            return False
        cell = pick()
        dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
        dom = list(dom); rng.shuffle(dom)
        for v in dom:
            st["nodes"] += 1
            add(cell)
            if v is not None: arcs[cell] = v
            if closure_capped(N, arcs, assigned, clues, area_cap):
                if rec(depth + 1):
                    rem(cell); arcs.pop(cell, None); return True
            rem(cell); arcs.pop(cell, None)
        return False

    rec(0)
    return sols, st


if __name__ == "__main__":
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    p = data.PUZZLE
    sols, st = solve(p["N"], p["clues"], p["green"], time_limit=tl, seed=seed)
    print(f"seed={seed} nodes={st['nodes']} maxd={st['maxd']}/81 "
          f"timeout={st['timeout']} sols={len(sols)}")
    for arcs, ans in sols[:1]:
        print("ANSWER", ans); print("ARCS", arcs)
