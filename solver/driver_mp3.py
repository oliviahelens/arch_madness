"""Merging-aware solver with fine-grained work-stealing shards for balance.

NSHARD logical shards; NW worker processes pull the next shard from a shared
counter (implicit load balancing). Each shard runs fillomino2 over a disjoint
slice of first-region placements; realize2 filters each tiling.
"""
import sys, time, json, multiprocessing as mp
import input as data
import fillomino2 as F
from realize2 import realize2

p = data.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]


def worker(nshard, rtl, tl, found, counter, lock, rq, pq, t0):
    local_tries = 0
    while not found.value and time.time() - t0 < tl:
        with lock:
            sidx = counter.value
            counter.value += 1
        if sidx >= nshard:
            break

        def on_tiling(owner, st):
            nonlocal local_tries
            if found.value:
                return True
            local_tries += 1
            sols, rst = realize2(N, clues, green, owner, time_limit=rtl, seed=0)
            if sols:
                found.value = 1
                rq.put((sidx, sols[0][1],
                        {f"{r},{c}": v for (r, c), v in sols[0][0].items()}))
                return True
            return False

        F.solve(N, clues, time_limit=max(1, tl - (time.time() - t0)), seed=None,
                on_tiling=on_tiling, shard=(sidx, nshard))
        pq.put((sidx, local_tries, round(time.time() - t0)))


if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 1700
    RTL = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    NW = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    NSHARD = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    found = mp.Value("i", 0)
    counter = mp.Value("i", 0)
    lock = mp.Lock()
    rq = mp.Queue(); pq = mp.Queue()
    t0 = time.time()
    procs = [mp.Process(target=worker,
                        args=(NSHARD, RTL, TL, found, counter, lock, rq, pq, t0))
             for _ in range(NW)]
    for pr in procs:
        pr.start()
    answer = None
    done_shards = 0
    while any(pr.is_alive() for pr in procs):
        time.sleep(2)
        while not pq.empty():
            sidx, tr, el = pq.get(); done_shards += 1
            print(f"progress shard {sidx} done ({done_shards} shards, {el}s, "
                  f"counter~{counter.value}/{NSHARD})", flush=True)
        if not rq.empty():
            sidx, ans, arcs = rq.get(); answer = (ans, arcs)
            print(f"\n*** SOLVED in shard {sidx}, {time.time()-t0:.0f}s ANSWER={ans} ***",
                  flush=True)
            with open("solution.json", "w") as f:
                json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
            print("saved solution.json", flush=True); break
    for pr in procs:
        pr.terminate()
    if answer is None and not rq.empty():
        sidx, ans, arcs = rq.get(); answer = (ans, arcs)
        with open("solution.json", "w") as f:
            json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
        print(f"*** SOLVED ANSWER={ans} ***", flush=True)
    if answer is None:
        print(f"no solution found in {time.time()-t0:.0f}s "
              f"(shards done: {done_shards}/{NSHARD})", flush=True)
    else:
        print("ANSWER:", answer[0], flush=True)
