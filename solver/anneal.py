"""Stochastic local search (simulated annealing) over arc configurations.

Backtracking commits depth-first and drowns in dead subtrees. Local search instead
keeps a FULL grid and nudges single cells to reduce a continuous "energy":

    E = Wg*(#dangling arcs + sum|disk-sliver| over regions)        # geometry validity
      + Wc*sum_over_clues |region_score - clue| / max(clue,1)      # clue satisfaction

E == 0 with valid geometry  <=>  a grid satisfying every clue (a solution).
The validated engine (regions + perimeter) supplies the energy; the user's oracle
confirms the final answer.
"""

import sys
import math
import random
from collections import defaultdict

from regions import DSU, all_pieces, piece_on_edge
from perimeter import analyze
from solver import interior_point, map_point_to_root, readout, score_regions
import input as data

VALUES = (None, "TL", "TR", "BL", "BR")


def energy(N, arcs, clues, Wg=2.0, Wc=1.0, geo_gate=2):
    dsu = DSU()
    pieces = all_pieces(N, arcs)
    for p in pieces:
        dsu.find(p)
    for r in range(N):
        for c in range(N):
            if c + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "R"), piece_on_edge(arcs, r, c + 1, "L"))
            if r + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "B"), piece_on_edge(arcs, r + 1, c, "T"))
    dangle = 0
    for (r, c) in arcs:
        if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
            dangle += 1
    full = defaultdict(int); disk = defaultdict(int); sliv = defaultdict(int)
    for p in pieces:
        root = dsu.find(p)
        full[root] += (p[2] == "W"); disk[root] += (p[2] == "D"); sliv[root] += (p[2] == "S")
    roots = set(dsu.find(p) for p in pieces)
    nonint = sum(abs(disk[root] - sliv[root]) for root in roots)
    geo = dangle + nonint

    # Expensive smooth-perimeter (analyze) only when geometry is near-valid.
    if geo > geo_gate:
        return Wg * geo + Wc * (len(clues) + 1.0), False

    root_of = {p: dsu.find(p) for p in pieces}
    faces = analyze(N, arcs)
    outer = max(faces, key=lambda f: f["area"])
    smooth = defaultdict(int)
    for f in faces:
        if f is outer:
            continue
        ip = interior_point(f)
        if ip is None:
            continue
        root = map_point_to_root(N, arcs, root_of, ip[0], ip[1])
        if root is not None:
            smooth[root] += f["smooth"]

    pen_c = 0.0
    exact_ok = True
    for (r, c), val in clues.items():
        root = root_of[(r, c, "W")] if (r, c) not in arcs else root_of[(r, c, "D")]
        area_est = full[root] + (disk[root] + sliv[root]) / 2.0
        score = area_est * smooth[root]
        pen_c += abs(score - val) / max(val, 1)
        if geo != 0 or score != val:
            exact_ok = False
    E = Wg * geo + Wc * pen_c
    solved = (geo == 0 and exact_ok)
    return E, solved


def anneal(N, clues, green, seed=0, steps=200000, T0=2.0, Tmin=0.02,
           Wg=2.0, Wc=1.0, reheat_after=8000):
    rng = random.Random(seed)
    free = [(r, c) for r in range(N) for c in range(N) if (r, c) not in green]
    # random start
    arcs = {}
    for cell in free:
        v = rng.choice(VALUES)
        if v is not None:
            arcs[cell] = v
    E, solved = energy(N, arcs, clues, Wg, Wc)
    best = E
    best_arcs = dict(arcs)
    since_improve = 0
    decay = (Tmin / T0) ** (1.0 / steps)
    T = T0
    for step in range(steps):
        if solved:
            break
        cell = rng.choice(free)
        old = arcs.get(cell)
        new = rng.choice(VALUES)
        while new == old:
            new = rng.choice(VALUES)
        if new is None:
            arcs.pop(cell, None)
        else:
            arcs[cell] = new
        E2, solved2 = energy(N, arcs, clues, Wg, Wc)
        dE = E2 - E
        if dE <= 0 or rng.random() < math.exp(-dE / T):
            E, solved = E2, solved2
            if E < best - 1e-9:
                best, best_arcs, since_improve = E, dict(arcs), 0
            else:
                since_improve += 1
        else:  # reject -> revert
            if old is None:
                arcs.pop(cell, None)
            else:
                arcs[cell] = old
            since_improve += 1
        T *= decay
        if since_improve > reheat_after:  # stuck -> reheat
            T = T0
            since_improve = 0
    return best, best_arcs, solved, energy(N, best_arcs, clues, Wg, Wc)[1]


def minconf(N, clues, green, seed=0, steps=300000, noise=0.25,
            Wg=2.0, Wc=1.0, restart_after=15000):
    """Min-conflicts local search. Start all-whole (valid geometry); repeatedly set
    a chosen cell to its best value, with `noise` probability of a random move.
    Random restart when stuck."""
    rng = random.Random(seed)
    free = [(r, c) for r in range(N) for c in range(N) if (r, c) not in green]
    arcs = {}
    E, solved = energy(N, arcs, clues, Wg, Wc)
    best, best_arcs = E, dict(arcs)
    stuck = 0
    for step in range(steps):
        if solved:
            break
        cell = rng.choice(free)
        old = arcs.get(cell)
        if rng.random() < noise:
            new = rng.choice(VALUES)
            if new is None:
                arcs.pop(cell, None)
            else:
                arcs[cell] = new
            E, solved = energy(N, arcs, clues, Wg, Wc)
        else:
            bestv, bestE, bestsolved = old, None, False
            for v in VALUES:
                if v is None:
                    arcs.pop(cell, None)
                else:
                    arcs[cell] = v
                Ev, sv = energy(N, arcs, clues, Wg, Wc)
                if bestE is None or Ev < bestE or (Ev == bestE and rng.random() < 0.5):
                    bestv, bestE, bestsolved = v, Ev, sv
            if bestv is None:
                arcs.pop(cell, None)
            else:
                arcs[cell] = bestv
            E, solved = bestE, bestsolved
        if E < best - 1e-9:
            best, best_arcs, stuck = E, dict(arcs), 0
        else:
            stuck += 1
        if stuck > restart_after:  # kick: randomize a handful of cells
            for _ in range(rng.randint(3, 8)):
                cc = rng.choice(free)
                vv = rng.choice(VALUES)
                if vv is None:
                    arcs.pop(cc, None)
                else:
                    arcs[cc] = vv
            E, solved = energy(N, arcs, clues, Wg, Wc)
            stuck = 0
    return best, best_arcs, solved


def energy_w(N, arcs, clues, weights, Wg=3.0, geo_gate=3):
    """Weighted energy for breakout local search. Returns (E, solved, violated set)."""
    dsu = DSU()
    pieces = all_pieces(N, arcs)
    for p in pieces:
        dsu.find(p)
    for r in range(N):
        for c in range(N):
            if c + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "R"), piece_on_edge(arcs, r, c + 1, "L"))
            if r + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "B"), piece_on_edge(arcs, r + 1, c, "T"))
    dangle = 0
    for (r, c) in arcs:
        if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
            dangle += 1
    full = defaultdict(int); disk = defaultdict(int); sliv = defaultdict(int)
    for p in pieces:
        root = dsu.find(p)
        full[root] += (p[2] == "W"); disk[root] += (p[2] == "D"); sliv[root] += (p[2] == "S")
    roots = set(dsu.find(p) for p in pieces)
    nonint = sum(abs(disk[root] - sliv[root]) for root in roots)
    geo = dangle + nonint
    if geo > geo_gate:
        return Wg * geo + sum(weights.values()), False, set(clues)

    root_of = {p: dsu.find(p) for p in pieces}
    faces = analyze(N, arcs)
    outer = max(faces, key=lambda f: f["area"])
    smooth = defaultdict(int)
    for f in faces:
        if f is outer:
            continue
        ip = interior_point(f)
        if ip is None:
            continue
        root = map_point_to_root(N, arcs, root_of, ip[0], ip[1])
        if root is not None:
            smooth[root] += f["smooth"]

    E = Wg * geo
    violated = set()
    for (r, c), val in clues.items():
        root = root_of[(r, c, "W")] if (r, c) not in arcs else root_of[(r, c, "D")]
        area_est = full[root] + (disk[root] + sliv[root]) / 2.0
        score = area_est * smooth[root]
        if geo != 0 or score != val:
            violated.add((r, c))
            E += weights[(r, c)] * (abs(score - val) / max(val, 1) + 0.3)
    return E, (geo == 0 and not violated), violated


def breakout(N, clues, green, seed=0, steps=400000, noise=0.12,
             Wg=3.0, geo_gate=3, plateau=40):
    rng = random.Random(seed)
    free = [(r, c) for r in range(N) for c in range(N) if (r, c) not in green]
    weights = {cell: 1.0 for cell in clues}
    arcs = {}
    E, solved, viol = energy_w(N, arcs, clues, weights, Wg, geo_gate)
    best_viol = len(viol)
    best_arcs = dict(arcs)
    since = 0
    for step in range(steps):
        if solved:
            break
        cell = rng.choice(free)
        old = arcs.get(cell)
        if rng.random() < noise:
            new = rng.choice(VALUES)
            if new is None:
                arcs.pop(cell, None)
            else:
                arcs[cell] = new
            E, solved, viol = energy_w(N, arcs, clues, weights, Wg, geo_gate)
        else:
            bestv, bestE, bestsolved, bestviol = old, None, False, viol
            for v in VALUES:
                if v is None:
                    arcs.pop(cell, None)
                else:
                    arcs[cell] = v
                Ev, sv, vv = energy_w(N, arcs, clues, weights, Wg, geo_gate)
                if bestE is None or Ev < bestE - 1e-9 or (abs(Ev - bestE) < 1e-9 and rng.random() < 0.4):
                    bestv, bestE, bestsolved, bestviol = v, Ev, sv, vv
            if bestv is None:
                arcs.pop(cell, None)
            else:
                arcs[cell] = bestv
            E, solved, viol = bestE, bestsolved, bestviol
        if len(viol) < best_viol:
            best_viol, best_arcs, since = len(viol), dict(arcs), 0
        else:
            since += 1
        if since >= plateau:  # stuck: raise weights on violated clues (breakout)
            for cell2 in viol:
                weights[cell2] += 1.0
            since = 0
            E, solved, viol = energy_w(N, arcs, clues, weights, Wg, geo_gate)
    return best_viol, best_arcs, solved


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "example"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    steps = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
    p = data.EXAMPLE if which == "example" else data.PUZZLE
    best, arcs, solved, ok = anneal(p["N"], p["clues"], p["green"], seed=seed, steps=steps)
    print(f"seed={seed} best_energy={best:.4f} solved={solved}")
    if solved:
        cs, _ = score_regions(p["N"], arcs)
        print(f"  *** SOLUTION answer={readout(p['N'], cs)}")
        print(f"      arcs={arcs}")
