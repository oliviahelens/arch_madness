"""Constrained grouped tiler.

Given a PLAN that fixes how equal-valued clues group into regions and each
region's size (from a feasible area profile), enumerate only the region SHAPES
(connected, containing the group's clue cells, avoiding other groups' clues),
prune with the sound shape oracle, and realize each full tiling with realize2.

This sidesteps the blind merge-discovery that stalled the unconstrained search.
"""
import sys, time, json
from collections import deque
import input as dd
import shapecheck as SC
from realize2 import realize2

p = dd.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]
SEA = (7, 8)
NB = ((0, 1), (1, 0), (0, -1), (-1, 0))

# Maximal-merge profile (area: 9s=9,15=5,21=7,25=10,27=9,35=5,45=5,63=7 -> 288=24)
PLAN = [
    # (required clue cells, size)   -- most constrained first
    ([(1, 4), (2, 1), (4, 3)], 9),     # 27 merged (smooth 3)
    ([(0, 2), (1, 0)], 7),             # 21 merged (smooth 3)
    ([(6, 3), (7, 1)], 7),             # 63 merged (smooth 9)
    ([(4, 5), (6, 7)], 5),             # 45 merged (smooth 9)
    ([(1, 7)], 5),                     # 25
    ([(4, 0)], 5),                     # 25
    ([(2, 5)], 5),                     # 15 (smooth 3)
    ([(8, 5)], 5),                     # 35 (smooth 7)
    ([(2, 8), (4, 8)], 3),             # 9 merged
    ([(6, 0)], 3),                     # 9
    ([(7, 4)], 3),                     # 9
]
ALL288AREA = (24,)

allclues = set(clues)


def neighbors(cell):
    r, c = cell
    for dr, dc in NB:
        n = (r + dr, c + dc)
        if 0 <= n[0] < N and 0 <= n[1] < N:
            yield n


def enum_shapes(required, size, free, forbidden_clues):
    """Yield connected cell-sets of exactly `size`, ⊇ required, ⊆ free, containing
    no forbidden clue cell. Canonical enumeration (avoid dups via ordered bans)."""
    req = set(required)
    if not req <= free:
        return
    results = []

    def grow(cur, banned):
        if len(cur) == size:
            results.append(frozenset(cur)); return
        # must still be able to include all required
        if not req <= (cur | (free - banned)):
            return
        # frontier: neighbours of cur (to stay connected) OR required not yet in
        front = set()
        for cell in cur:
            for n in neighbors(cell):
                if n in free and n not in cur and n not in banned:
                    front.add(n)
        # also if some required not adjacent yet, allow reaching them via frontier
        if not front:
            return
        front = sorted(front)
        local_ban = set(banned)
        for n in front:
            # prune forbidden clue cells
            if n in forbidden_clues:
                local_ban.add(n); continue
            grow(cur | {n}, local_ban)
            local_ban.add(n)

    # seed must be connected containing all required: start from required's
    # connected hull by growing from one required cell; require ⊇ req at the end.
    start = set(req)
    # if required cells aren't mutually connected, grow() will connect them via free
    if len(start) > size:
        return
    grow(start, set())
    seen = set()
    for r in results:
        if req <= r and r not in seen:
            seen.add(r)
            yield r


def connected(cells):
    cells = set(cells)
    if not cells:
        return False
    st = [next(iter(cells))]; seen = {st[0]}
    while st:
        x = st.pop()
        for n in neighbors(x):
            if n in cells and n not in seen:
                seen.add(n); st.append(n)
    return len(seen) == len(cells)


def solve(time_limit=1800):
    t0 = time.time()
    print("cache:", SC.load_cache(), flush=True)
    owner = {}
    region_clue_cells = [set(rc) for rc, _ in PLAN]
    # forbidden clues for a region = all clue cells not in that region's group
    stats = {"tilings": 0, "nodes": 0}

    def place(i):
        if time.time() - t0 > time_limit:
            return False
        if i == len(PLAN):
            return finish()
        required, size = PLAN[i]
        v = clues[required[0]]
        free = frozenset((r, c) for r in range(N) for c in range(N)
                         if (r, c) not in owner)
        forbidden = (allclues - set(required)) | {SEA}
        for shape in enum_shapes(required, size, free, forbidden):
            stats["nodes"] += 1
            # sound oracle prune (small regions)
            if size <= 6:
                if SC.can_realize_shape(shape, N, v // size,
                                        time_budget=3.0, green=green) is False:
                    continue
            for cell in shape:
                owner[cell] = i
            if place(i + 1):
                return True
            for cell in shape:
                del owner[cell]
        return False

    def finish():
        left = [(r, c) for r in range(N) for c in range(N) if (r, c) not in owner]
        if len(left) not in ALL288AREA:
            return False
        if SEA not in set(left) or not connected(left):
            return False
        full = dict(owner)
        for cell in left:
            full[cell] = "S288"
        stats["tilings"] += 1
        if stats["tilings"] % 50 == 0:
            print(f"  [{time.time()-t0:.0f}s] tilings={stats['tilings']} "
                  f"nodes={stats['nodes']}", flush=True)
        sols, _ = realize2(N, clues, green, full, time_limit=6.0, seed=0)
        if sols:
            ans = sols[0][1]
            arcs = {f"{r},{c}": a for (r, c), a in sols[0][0].items()}
            json.dump({"answer": ans, "arcs": arcs}, open("solution.json", "w"), indent=2)
            print(f"\n*** SOLVED ANSWER={ans} (tiling #{stats['tilings']}, "
                  f"{time.time()-t0:.0f}s) -> solution.json ***", flush=True)
            return True
        return False

    ok = place(0)
    SC.save_cache()
    print(f"done: solved={ok} tilings={stats['tilings']} nodes={stats['nodes']} "
          f"in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    solve(int(sys.argv[1]) if len(sys.argv) > 1 else 1800)
