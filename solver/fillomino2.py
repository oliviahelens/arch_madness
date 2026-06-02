"""Merging-aware Fillomino tiling.

Partition the grid into connected regions. Each region contains >=1 clue cell,
all of the SAME value v, and has size (cell count) in ALLOWED[v]. Same-valued
clues may merge into one region. The 288 region is the LEFTOVER (never
enumerated as subsets). Regions tile all 81 cells (no unclued region).

Streams complete tilings to a callback (e.g. realize2).
"""
import sys, time, random
from collections import deque
import input as data

# per-value allowed region sizes (area). Tight-but-reasonable; broaden if needed.
ALLOWED = {
    # area-3 maxes at smooth 7, so clue 27 (needs smooth 9) cannot be size 3
    # -> size 9 (smooth 3). A single 9-clue at size 9 (smooth 1) is implausible.
    9: (3,), 15: (3, 5), 21: (3, 7), 25: (5,), 27: (9,),
    35: (5, 7), 45: (5, 9), 63: (7, 9),
}
ALLOWED_288 = (12, 16, 18, 24, 32, 36, 48)
SEA = (7, 8)            # the 288 clue cell -> leftover region
NB = ((0, 1), (1, 0), (0, -1), (-1, 0))


def solve(N, clues, time_limit=600, seed=None, on_tiling=None, verbose=False,
          shard=(0, 1)):
    rng = random.Random(seed) if seed is not None else None
    seedset = set(clues)
    grow_order = [c for c in clues if c != SEA]
    # process order: regions with larger max size later (small first), 288 leftover
    grow_order.sort(key=lambda c: (max(ALLOWED[clues[c]]),
                                    rng.random() if rng else c))
    shard_id, shard_mod = shard
    st_branch = [0]   # counts top-level (first-region) completions for sharding
    owner = {}
    covered = set()
    start = time.time()
    st = {"nodes": 0, "tilings": 0, "to": False}

    from functools import lru_cache

    def build_ach(v):
        opts = ALLOWED[v]
        @lru_cache(maxsize=None)
        def ach(k):
            if k == 0:
                return frozenset({0})
            out = set()
            for j in range(1, k + 1):       # first group covers j clue cells
                for s in opts:
                    if s >= j:
                        for rest in ach(k - j):
                            out.add(s + rest)
            return frozenset(out)
        return ach
    ACH = {v: build_ach(v) for v in set(clues.values()) if v in ALLOWED}

    def free(cell):
        return cell not in owner

    def feasible():
        """Each connected free component must be EXACTLY tileable by the uncovered
        clues inside it (subset-sum over allowed region sizes); the SEA component
        must additionally leave a valid 288-size remainder."""
        visited = set()
        for sr in range(N):
            for sc in range(N):
                if (sr, sc) in visited or not free((sr, sc)):
                    continue
                dq = deque([(sr, sc)]); visited.add((sr, sc))
                size = 0; counts = {}; has_sea = False
                while dq:
                    cell = dq.popleft(); size += 1
                    if cell == SEA:
                        has_sea = True
                    elif cell in seedset and cell not in covered:
                        v = clues[cell]; counts[v] = counts.get(v, 0) + 1
                    for dr, dc in NB:
                        n = (cell[0] + dr, cell[1] + dc)
                        if 0 <= n[0] < N and 0 <= n[1] < N and free(n) and n not in visited:
                            visited.add(n); dq.append(n)
                totals = {0}
                for v, k in counts.items():
                    av = ACH[v](k)
                    totals = {t + a for t in totals for a in av}
                    if not totals:
                        return False
                if has_sea:
                    if not any((size - t) in ALLOWED_288 for t in totals):
                        return False
                else:
                    if size not in totals:
                        return False
        return True

    def finish():
        # leftover free cells must form the 288 region
        left = [(r, c) for r in range(N) for c in range(N) if free((r, c))]
        if not left:
            return False
        if len(left) not in ALLOWED_288:
            st['rej_size']=st.get('rej_size',0)+1
            return False
        if SEA not in set(left):
            return False
        # no other clue among leftover
        for cell in left:
            if cell in seedset and cell != SEA:
                return False
        # connected
        ls = set(left); dq = deque([SEA]); seen = {SEA}
        while dq:
            r, c = dq.popleft()
            for dr, dc in NB:
                n = (r + dr, c + dc)
                if n in ls and n not in seen:
                    seen.add(n); dq.append(n)
        if len(seen) != len(left):
            st['rej_disc']=st.get('rej_disc',0)+1
            return False
        # build full owner with SEA region
        full = dict(owner)
        for cell in left:
            full[cell] = SEA
        st['rej_ok']=st.get('rej_ok',0)+1
        st["tilings"] += 1
        if on_tiling is not None:
            return on_tiling(full, st)
        return False

    def next_region(gi):
        if st["to"] or time.time() - start > time_limit:
            st["to"] = True; return True
        while gi < len(grow_order) and grow_order[gi] in covered:
            gi += 1
        if gi > st.get("maxgi", -1):
            st["maxgi"] = gi
        if gi == len(grow_order):
            return finish()
        C = grow_order[gi]
        v = clues[C]
        for A in ALLOWED[v]:
            if enum_region(C, v, A, gi):
                return True
        return False

    def enum_region(C, v, A, gi):
        # enumerate connected A-subsets containing C from free cells, excluding
        # different-valued clue cells; same-valued clues get covered.
        members = [C]
        owner[C] = C
        newly = []
        if C in seedset and C != C:
            pass
        res = grow(C, v, A, members, set(), gi, newly)
        owner.pop(C, None)
        return res

    def grow(C, v, A, members, banned, gi, newly_covered):
        if st["to"]:
            return True
        if len(members) == A:
            # mark this region's clue cells (seed + any merged same-valued) covered
            added = []
            for cell in members:
                if cell in seedset and cell not in covered:
                    covered.add(cell); added.append(cell)
            ok = False
            do_recurse = True
            if gi == 1 and shard_mod > 1:     # shard on first TWO regions (finer)
                b = st_branch[0]; st_branch[0] += 1
                do_recurse = (b % shard_mod == shard_id)
            if do_recurse and feasible():
                ok = next_region(gi + 1)
            for cell in added:
                covered.discard(cell)
            return ok
        frontier = []
        seenf = set()
        for (r, c) in members:
            for dr, dc in NB:
                n = (r + dr, c + dc)
                if (0 <= n[0] < N and 0 <= n[1] < N and free(n)
                        and n not in banned and n not in seenf):
                    # cannot include a different-valued clue cell
                    if n in seedset and clues.get(n) != v:
                        continue
                    seenf.add(n); frontier.append(n)
        if not frontier:
            return False
        frontier.sort()
        if rng is not None:
            rng.shuffle(frontier)
        local_ban = set(banned)
        for n in frontier:
            st["nodes"] += 1
            owner[n] = C
            members.append(n)
            if grow(C, v, A, members, local_ban, gi, newly_covered):
                members.pop(); owner.pop(n); return True
            members.pop(); owner.pop(n)
            local_ban.add(n)
        return False

    next_region(0)
    return st


if __name__ == "__main__":
    p = data.PUZZLE
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cnt = [0]
    def cb(owner, st):
        cnt[0] += 1
        if cnt[0] <= 1:
            from fillomino import show
            print("first merged tiling:"); show(owner, p["N"], p["clues"])
        return cnt[0] >= 200000
    st = solve(p["N"], p["clues"], time_limit=tl, seed=None, on_tiling=cb)
    print(f"tilings found: {cnt[0]} nodes={st['nodes']} timeout={st['to']}")
