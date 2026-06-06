"""Oracle-pruned solve with a persistent shape-realizability cache.

Single process: load the shape cache, run the merging tiling enumeration with
the SOUND shape oracle pruning small regions (size<=oracle_max), realize each
surviving tiling with realize2 (engine-verified), and periodically persist the
cache so the expensive oracle work is computed once and reused across runs.
"""
import sys, time, json
import input as d
import fillomino2 as F
import shapecheck as SC
from realize2 import realize2

p = d.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]


def main():
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    OMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    print("loaded cache entries:", SC.load_cache(), flush=True)
    SC.AUTOSAVE[0] = True
    t0 = time.time()
    state = {"tilings": 0, "last_save": time.time(), "last_n": 0}

    def on_tiling(owner, st):
        state["tilings"] += 1
        sols, _ = realize2(N, clues, green, owner, time_limit=5.0, seed=0)
        if sols:
            ans = sols[0][1]
            arcs = {f"{r},{c}": v for (r, c), v in sols[0][0].items()}
            with open("solution.json", "w") as f:
                json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
            print(f"\n*** SOLVED  ANSWER={ans}  (tiling #{state['tilings']}, "
                  f"{time.time()-t0:.0f}s) -> solution.json ***", flush=True)
            SC.save_cache()
            return True
        now = time.time()
        if now - state["last_save"] > 30:
            saved = SC.save_cache()
            print(f"  [{now-t0:.0f}s] tilings={state['tilings']} "
                  f"cache={saved} ({len(SC._cache)}) "
                  f"rate={(state['tilings']-state['last_n'])/(now-state['last_save']):.1f}/s",
                  flush=True)
            state["last_save"] = now; state["last_n"] = state["tilings"]
        return False

    F.solve(N, clues, time_limit=TL, seed=seed, on_tiling=on_tiling,
            green=green, oracle=True, oracle_max=OMAX)
    SC.save_cache()
    print(f"done: tilings={state['tilings']} in {time.time()-t0:.0f}s "
          f"cache={len(SC._cache)}", flush=True)


if __name__ == "__main__":
    main()
