"""Multiprocessing driver: N workers stream Fillomino tilings (different random
orders) and realize each (partition-enforced). First solution wins."""
import sys, time, json, multiprocessing as mp
import input as data
from fillomino import solve_tilings
from realize import realize

p = data.PUZZLE
N, clues, green = p["N"], p["clues"], p["green"]


def worker(seed, realize_tl, time_limit, found_flag, result_q, prog_q):
    tries = 0
    t0 = time.time()

    def on_tiling(owner, st):
        nonlocal tries
        if found_flag.value:
            return True
        tries += 1
        sols, rst = realize(N, clues, green, owner, time_limit=realize_tl, seed=0)
        if sols:
            found_flag.value = 1
            result_q.put((seed, sols[0][1],
                          {f"{r},{c}": v for (r, c), v in sols[0][0].items()}, tries))
            return True
        if tries % 200 == 0:
            prog_q.put((seed, tries, round(time.time() - t0)))
        return False

    solve_tilings(N, clues, max_sols=1, time_limit=time_limit, verbose=False,
                  on_tiling=on_tiling, seed=seed)
    prog_q.put((seed, tries, round(time.time() - t0), "DONE"))


if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    RTL = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    NW = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    found = mp.Value("i", 0)
    rq = mp.Queue()
    pq = mp.Queue()
    procs = [mp.Process(target=worker, args=(s + 1, RTL, TL, found, rq, pq))
             for s in range(NW)]
    for pr in procs:
        pr.start()
    t0 = time.time()
    answer = None
    while any(pr.is_alive() for pr in procs):
        time.sleep(2)
        while not pq.empty():
            print("progress", pq.get(), flush=True)
        if not rq.empty():
            seed, ans, arcs, tries = rq.get()
            answer = (ans, arcs)
            print(f"\n*** SOLVED by seed{seed} after {tries} tilings, "
                  f"{time.time()-t0:.0f}s  ANSWER={ans} ***", flush=True)
            with open("solution.json", "w") as f:
                json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
            print("saved solution.json", flush=True)
            break
    for pr in procs:
        pr.terminate()
    if answer is None:
        # drain queue in case a solution arrived at the end
        if not rq.empty():
            seed, ans, arcs, tries = rq.get()
            answer = (ans, arcs)
            with open("solution.json", "w") as f:
                json.dump({"answer": ans, "arcs": arcs}, f, indent=2)
            print(f"*** SOLVED ANSWER={ans} ***", flush=True)
        else:
            print(f"no solution found in {time.time()-t0:.0f}s", flush=True)
    else:
        print("ANSWER:", answer[0], flush=True)
