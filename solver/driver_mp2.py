"""Merging-aware parallel solver: fillomino2 tilings -> realize2, first wins."""
import sys, time, json, multiprocessing as mp
import input as data
import fillomino2 as F
from realize2 import realize2

p = data.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]


def worker(wid, nw, rtl, tl, found, rq, pq):
    tries = 0; t0 = time.time()

    def on_tiling(owner, st):
        nonlocal tries
        if found.value:
            return True
        tries += 1
        sols, rst = realize2(N, clues, green, owner, time_limit=rtl, seed=0)
        if sols:
            found.value = 1
            rq.put((wid, sols[0][1],
                    {f"{r},{c}": v for (r, c), v in sols[0][0].items()}, tries))
            return True
        if tries % 500 == 0:
            pq.put((wid, tries, round(time.time() - t0)))
        return False

    # deterministic fast order; disjoint shard of first-region placements
    F.solve(N, clues, time_limit=tl, seed=None, on_tiling=on_tiling, shard=(wid, nw))
    pq.put((wid, tries, round(time.time() - t0), "DONE"))


if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    RTL = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    NW = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    found = mp.Value("i", 0); rq = mp.Queue(); pq = mp.Queue()
    procs = [mp.Process(target=worker, args=(s, NW, RTL, TL, found, rq, pq))
             for s in range(NW)]
    for pr in procs:
        pr.start()
    t0 = time.time(); answer = None
    while any(pr.is_alive() for pr in procs):
        time.sleep(2)
        while not pq.empty():
            print("progress", pq.get(), flush=True)
        if not rq.empty():
            seed, ans, arcs, tries = rq.get(); answer = (ans, arcs)
            print(f"\n*** SOLVED by seed{seed} after {tries} tilings, "
                  f"{time.time()-t0:.0f}s  ANSWER={ans} ***", flush=True)
            with open("solution.json", "w") as f:
                json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
            print("saved solution.json", flush=True); break
    for pr in procs:
        pr.terminate()
    if answer is None and not rq.empty():
        seed, ans, arcs, tries = rq.get(); answer = (ans, arcs)
        with open("solution.json", "w") as f:
            json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
        print(f"*** SOLVED ANSWER={ans} ***", flush=True)
    if answer is None:
        print(f"no solution found in {time.time()-t0:.0f}s", flush=True)
    else:
        print("ANSWER:", answer[0], flush=True)
