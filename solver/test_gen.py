"""Stress-test engine + solver pruning on random valid 4x4 (and 5x5) configs.

Soundness is guaranteed by construction: the solver only emits a leaf after
score_regions + clues_ok (the validated engine) accept it.

The real risk is COMPLETENESS: could the frontier-closure pruning ever wrongly
reject a valid configuration? We test this directly: take a ground-truth grid G
(random arcs the engine deems valid), derive its clues, then walk G's row-major
prefixes and assert closure_ok stays True the whole way -- i.e. the search would
never prune G. We also run the full solver on a few instances end-to-end to
confirm it actually finds a clue-consistent solution.
"""

import random
import sys

from solver import score_regions, readout, clues_ok
import backtrack

ARC_DIRS = ("TL", "TR", "BL", "BR")


def random_valid_grid(N, p_arc, rng):
    arcs = {}
    for r in range(N):
        for c in range(N):
            if rng.random() < p_arc:
                arcs[(r, c)] = rng.choice(ARC_DIRS)
    res = score_regions(N, arcs)
    if res is None:
        return None
    return arcs, res[0]


def prefix_survives(N, G_arcs, clues):
    order = [(r, c) for r in range(N) for c in range(N)]
    arcs, assigned = {}, set()
    for (r, c) in order:
        v = G_arcs.get((r, c))
        assigned.add((r, c))
        if v is not None:
            arcs[(r, c)] = v
        if not backtrack.closure_ok(N, arcs, assigned, clues):
            return (r, c)  # would be pruned here -> completeness bug
    return None


def run(N=4, trials=60, seed=0, end_to_end=4):
    rng = random.Random(seed)
    valid = 0
    skipped = 0
    prune_bugs = 0
    e2e_ok = 0
    e2e_run = 0
    while valid < trials:
        g = random_valid_grid(N, rng.uniform(0.30, 0.60), rng)
        if g is None:
            skipped += 1
            if skipped > trials * 400:
                print("  (gave up generating; low yield)")
                break
            continue
        arcs, cs = g
        valid += 1
        all_cells = [(r, c) for r in range(N) for c in range(N)]
        k = rng.randint(max(2, len(all_cells) // 3), 2 * len(all_cells) // 3)
        clue_cells = rng.sample(all_cells, k)
        clues = {cell: cs[cell] for cell in clue_cells}

        bug = prefix_survives(N, arcs, clues)
        if bug is not None:
            prune_bugs += 1
            print(f"[{valid}] PRUNE BUG: valid grid pruned at {bug}")
            print(f"     arcs={arcs}")
            print(f"     clues={clues}")

        # End-to-end: run the real solver on the first few, early-exit on G's answer.
        if e2e_run < end_to_end:
            green = frozenset(c for c in all_cells if c not in arcs)
            want = readout(N, cs)
            sols, stats = backtrack.solve(N, clues, green, time_limit=30, want=want)
            e2e_run += 1
            found = any(
                (lambda r: r is not None and clues_ok(r[0], clues))(score_regions(N, sa))
                for sa, _ in sols
            )
            tag = "FOUND" if found else ("timeout" if stats["timeout"] else "NO SOL")
            print(f"[{valid}] end-to-end: {tag} (sols={len(sols)}, nodes={stats['nodes']}, "
                  f"arcs={len(arcs)}, clues={len(clues)})")
            if found:
                e2e_ok += 1

    print(f"\nSUMMARY N={N}: valid_grids_tested={valid}  prune_bugs={prune_bugs}  "
          f"end_to_end_found={e2e_ok}/{e2e_run}  invalid_random_skipped={skipped}")


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    t = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    s = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    run(N=N, trials=t, seed=s)
