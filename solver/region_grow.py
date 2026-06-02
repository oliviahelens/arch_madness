"""Region-at-a-time backtracker.

Process clue regions one by one (most-constrained / smallest first). For the
current clue, grow its region by assigning frontier cells until the region
SEALS, at which point closure_ok validates it EXACTLY (integer area, no
dangling, exact smooth-score). This makes the strong exact prune fire within
~10-15 assignments instead of ~40, so wrong early choices die fast.

The biggest clue (the "sea") is left out of the queue and handled in a final
phase that assigns all remaining cells, then the full engine verifies every
clue (including the sea's).
"""
import sys, time, random
from collections import defaultdict
from regions import DSU, piece_on_edge
from backtrack import closure_ok, partial_components, is_open
from solver import score_regions, readout, clues_ok
import input as data

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))


def label_piece(cell, arcs):
    return (cell[0], cell[1], "W") if cell not in arcs else (cell[0], cell[1], "D")


def focus_frontier(N, arcs, assigned, cluecell):
    """Unassigned cells adjacent to an OPEN piece of cluecell's region.
    Returns list of frontier cells (deduped), or None if region already sealed."""
    dsu, comp = partial_components(N, arcs, assigned)
    root = dsu.find(label_piece(cluecell, arcs))
    pieces = comp[root]
    EDGE_NB = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}
    frontier = []
    seen = set()
    for p in pieces:
        r, c, _ = p
        for d, (dr, dc) in EDGE_NB.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < N and 0 <= nc < N and (nr, nc) not in assigned:
                if piece_on_edge(arcs, r, c, d) == p and (nr, nc) not in seen:
                    seen.add((nr, nc)); frontier.append((nr, nc))
    return frontier if frontier else None


def solve(N, clues, green, time_limit=120, seed=0, want=None,
          sea_clue=None, progress=False):
    allcells = [(r, c) for r in range(N) for c in range(N)]
    rng = random.Random(seed)

    # Queue order: every clue except the designated sea, most-constrained first.
    # Constrainedness ~ small value, near border, near greens.
    def constraint_key(cell):
        r, c = cell
        edge = min(r, N - 1 - r) + min(c, N - 1 - c)
        gn = sum((r + dr, c + dc) in green for dr, dc in NB)
        return (clues[cell], edge, -gn, rng.random())
    queue = sorted([c for c in clues if c != sea_clue], key=constraint_key)

    assigned = set()
    arcs = {}
    sols = []
    start = time.time()
    stats = {"nodes": 0, "phase": 0, "timeout": False, "best_phase": 0}

    def time_up():
        if time.time() - start > time_limit:
            stats["timeout"] = True
            return True
        return False

    def assign_cell(cell, v, cont):
        """Try assigning cell=v, check closure, call cont() if ok. Returns True to stop."""
        stats["nodes"] += 1
        assigned.add(cell)
        if v is not None:
            arcs[cell] = v
        res = False
        if closure_ok(N, arcs, assigned, clues):
            res = cont()
        assigned.discard(cell)
        arcs.pop(cell, None)
        return res

    def grow(qi, cluecell):
        """Grow cluecell's region to closure, then advance to queue[qi+1]."""
        if stats["timeout"] or time_up():
            return True
        # ensure clue cell itself assigned first
        if cluecell not in assigned:
            dom = (None,) if cluecell in green else (None, "TL", "TR", "BL", "BR")
            dom = list(dom); rng.shuffle(dom)
            for v in dom:
                if assign_cell(cluecell, v, lambda: grow(qi, cluecell)):
                    return True
            return False
        front = focus_frontier(N, arcs, assigned, cluecell)
        if front is None:
            # region sealed & validated -> next clue
            return next_clue(qi + 1)
        cell = front[0]
        dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
        dom = list(dom); rng.shuffle(dom)
        for v in dom:
            if assign_cell(cell, v, lambda: grow(qi, cluecell)):
                return True
        return False

    def next_clue(qi):
        if qi > stats["best_phase"]:
            stats["best_phase"] = qi
            if progress:
                print(f"  seed{seed} closed {qi}/{len(queue)} clue-regions "
                      f"nodes={stats['nodes']} {stats['nodes']/(time.time()-start):.0f}/s",
                      flush=True)
        if qi == len(queue):
            return finish()
        return grow(qi, queue[qi])

    def finish():
        """All queued clue regions sealed. Assign remaining cells, verify all."""
        rem = [c for c in allcells if c not in assigned]
        def rec(i):
            if stats["timeout"] or time_up():
                return True
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
                if assign_cell(cell, v, lambda: rec(i + 1)):
                    return True
            return False
        return rec(0)

    next_clue(0)
    return sols, stats


if __name__ == "__main__":
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    which = sys.argv[3] if len(sys.argv) > 3 else "puzzle"
    if which == "example":
        p = data.EXAMPLE
        sols, stats = solve(p["N"], p["clues"], p["green"], time_limit=tl,
                            seed=seed, want=p["answer"], sea_clue=(3, 3), progress=True)
    else:
        p = data.PUZZLE
        sols, stats = solve(p["N"], p["clues"], p["green"], time_limit=tl,
                            seed=seed, sea_clue=(7, 8), progress=True)
    print(f"seed={seed} nodes={stats['nodes']} best_phase={stats['best_phase']} "
          f"timeout={stats['timeout']} sols={len(sols)}")
    for arcs, ans in sols[:2]:
        print("answer", ans)
