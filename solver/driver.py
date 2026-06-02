"""Stream Fillomino tilings; realize arcs for each; stop at first solution."""
import sys, time
import input as data
from fillomino import solve_tilings
from realize import realize

p = data.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]
TL = int(sys.argv[1]) if len(sys.argv) > 1 else 600
REALIZE_TL = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
TSEED = int(sys.argv[3]) if len(sys.argv) > 3 else None

state = {"found": None, "tries": 0, "t0": time.time()}


def on_tiling(owner, st):
    state["tries"] += 1
    sols, rst = realize(N, clues, green, owner, time_limit=REALIZE_TL, seed=0)
    if sols:
        state["found"] = (owner, sols[0])
        arcs, ans = sols[0]
        print(f"\n*** SOLVED after {state['tries']} tilings, "
              f"{time.time()-state['t0']:.0f}s  ANSWER={ans} ***", flush=True)
        return True
    if state["tries"] % 50 == 0:
        print(f"  [seed{TSEED}] tried {state['tries']} tilings, "
              f"{time.time()-state['t0']:.0f}s, tiling-nodes={st['nodes']}", flush=True)
    return False


solve_tilings(N, clues, max_sols=1, time_limit=TL, verbose=False, on_tiling=on_tiling,
              seed=TSEED)

if state["found"]:
    owner, (arcs, ans) = state["found"]
    print("ANSWER:", ans)
    print("ARCS:", arcs)
    import json
    with open("solution.json", "w") as f:
        json.dump({"answer": ans, "arcs": {f"{r},{c}": v for (r, c), v in arcs.items()}},
                  f, indent=2)
    print("saved solution.json")
else:
    print(f"no solution found ({state['tries']} tilings tried, "
          f"{time.time()-state['t0']:.0f}s)")
