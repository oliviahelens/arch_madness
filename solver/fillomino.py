"""Fillomino-style tiling: partition the grid into connected polyominoes, one
per clue, of sizes = pinned region areas (candidate generator for arcs).

areas: 9->3 15->3 21->3 25->5 27->3 35->5 45->5 63->7 288->12
"""
import sys, time, random
from collections import deque
import input as data

AREA = {9: 3, 15: 3, 21: 3, 25: 5, 27: 3, 35: 5, 45: 5, 63: 7, 288: 12}
NB = ((0, 1), (1, 0), (0, -1), (-1, 0))


def solve_tilings(N, clues, max_sols=5, time_limit=600, verbose=True, on_tiling=None,
                  seed=None):
    rng = random.Random(seed) if seed is not None else None
    seeds = list(clues)
    seedset = set(seeds)
    sizes = {s: AREA[clues[s]] for s in seeds}
    owner = {s: s for s in seeds}            # cell -> seed
    region_order = sorted(seeds, key=lambda s: (sizes[s], rng.random() if rng else s))
    order_idx = {s: i for i, s in enumerate(region_order)}
    sols = []
    start = time.time()
    st = {"nodes": 0, "to": False}

    def free(cell):
        return cell not in owner

    def feasible(next_i):
        """Global check: remaining free cells must be claimable.
        - every free cell reachable (orthogonally, through free cells) from the
          region-set of some incomplete seed, within its remaining budget is too
          expensive; use: every free cell is in a free-component that contains/
          borders >=1 incomplete seed, and component size == sum of borrowing
          seeds' remaining capacities is too strong. We use two cheap necessary
          checks:
          (1) each incomplete seed can reach >= (size-current) free cells.
          (2) no free cell is unreachable from EVERY incomplete seed's frontier
              region (i.e. orphaned)."""
        incomplete = [s for s in region_order[next_i:]]
        # current member sets
        members = {}
        for s in incomplete:
            members[s] = []
        for cell, s in owner.items():
            if s in members:
                members[s].append(cell)
        # (1) reachable free-space from each incomplete region
        reachable_union = set()
        for s in incomplete:
            need = sizes[s] - len(members[s])
            seen = set(members[s]); dq = deque(members[s]); cnt = 0
            while dq:
                r, c = dq.popleft()
                for dr, dc in NB:
                    n = (r + dr, c + dc)
                    if 0 <= n[0] < N and 0 <= n[1] < N and n not in seen and free(n):
                        seen.add(n); dq.append(n); cnt += 1
            if cnt < need:
                return False
            reachable_union |= (seen - set(members[s]))
        # (2) every free cell reachable from some incomplete seed
        nfree = sum(1 for r in range(N) for c in range(N) if free((r, c)))
        # reachable_union counts free cells reachable from some incomplete region
        freecells = set((r, c) for r in range(N) for c in range(N) if free((r, c)))
        if not freecells <= reachable_union:
            return False
        return True

    def advance(done_seed):
        if st["to"] or time.time() - start > time_limit:
            st["to"] = True; return True
        i = order_idx[done_seed] + 1
        if i == len(region_order):
            if len(owner) == N * N:
                st["tilings"] = st.get("tilings", 0) + 1
                if on_tiling is not None:
                    if on_tiling(dict(owner), st):
                        return True          # callback says stop
                    return False             # keep searching, don't store
                sols.append(dict(owner))
                if verbose:
                    print(f"  tiling #{len(sols)} (nodes={st['nodes']}, "
                          f"{time.time()-start:.0f}s)", flush=True)
                return len(sols) >= max_sols
            return False
        if not feasible(i):
            return False
        return enum_region(region_order[i], [region_order[i]], set())

    def enum_region(s, members, banned):
        if st["to"] or time.time() - start > time_limit:
            st["to"] = True; return True
        if len(members) == sizes[s]:
            return advance(s)
        frontier = []
        seenf = set()
        for (r, c) in members:
            for dr, dc in NB:
                n = (r + dr, c + dc)
                if (0 <= n[0] < N and 0 <= n[1] < N and free(n)
                        and n not in seedset and n not in banned and n not in seenf):
                    seenf.add(n); frontier.append(n)
        if not frontier:
            return False
        frontier.sort()
        if rng is not None:
            rng.shuffle(frontier)
        local_ban = set(banned)
        for n in frontier:
            st["nodes"] += 1
            owner[n] = s
            members.append(n)
            if enum_region(s, members, local_ban):
                members.pop(); owner.pop(n); return True
            members.pop(); owner.pop(n)
            local_ban.add(n)
        return False

    first = region_order[0]
    if sizes[first] == 1:
        advance(first)
    else:
        enum_region(first, [first], set())
    return sols, st


def show(owner, N, clues):
    for r in range(N):
        print(" ".join(f"{clues[owner[(r,c)]]:>3}" for c in range(N)))


if __name__ == "__main__":
    p = data.PUZZLE
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tl = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    sols, st = solve_tilings(p["N"], p["clues"], max_sols=cap, time_limit=tl)
    print(f"tilings found (cap {cap}): {len(sols)} nodes={st['nodes']} timeout={st['to']}")
    if sols:
        print("first tiling (clue value per cell):")
        show(sols[0], p["N"], p["clues"])
