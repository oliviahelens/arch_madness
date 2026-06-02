"""Independently verify solution.json: re-run the engine on the arcs, confirm
every clue's region score matches, and recompute the read-out answer."""
import json, sys
from solver import score_regions, readout
import input as data

p = data.PUZZLE
N, clues = p["N"], p["clues"]
with open(sys.argv[1] if len(sys.argv) > 1 else "solution.json") as f:
    sol = json.load(f)
arcs = {tuple(int(x) for x in k.split(",")): v for k, v in sol["arcs"].items()}

# greens must have no arc
for g in p["green"]:
    assert g not in arcs, f"green {g} has an arc!"

res = score_regions(N, arcs)
assert res is not None, "engine REJECTS arcs (invalid geometry)"
cs, info = res

print("clue check:")
all_ok = True
for cell, val in sorted(clues.items()):
    got = cs[cell]
    ok = (got == val)
    all_ok &= ok
    print(f"  {cell} expect {val:>3} got {got:>3} {'OK' if ok else 'MISMATCH'}")

ans = readout(N, cs)
print(f"\nall clues satisfied: {all_ok}")
print(f"recomputed answer: {ans}  (file says {sol['answer']})")
print(f"match: {ans == sol['answer']}")

print("\nscore grid:")
for r in range(N):
    print(" ".join(f"{cs[(r,c)]:>3}" for c in range(N)))
