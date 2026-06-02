"""Randomized-restart driver. Cycles through seeds, each a short budget; stops at
the first full clue-consistent solution found. Run several in parallel (one per
core) over disjoint seed sets.

Usage: python3 restarts.py puzzle "1,2,3" 60   # seeds, per-seed seconds
"""
import sys
import backtrack as B
import input as data

which = sys.argv[1] if len(sys.argv) > 1 else "puzzle"
seeds = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]
per = int(sys.argv[3]) if len(sys.argv) > 3 else 60

p = data.PUZZLE if which == "puzzle" else data.EXAMPLE
for sd in seeds:
    sols, st = B.solve(p["N"], p["clues"], p["green"], time_limit=per,
                       seed=sd, stop_first=True)
    print(f"seed {sd}: nodes={st['nodes']} timeout={st['timeout']} sols={len(sols)}",
          flush=True)
    if sols:
        for arcs, ans in sols:
            print(f"  *** FOUND answer={ans}", flush=True)
            print(f"      arcs={arcs}", flush=True)
        break
