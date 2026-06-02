"""Merging-aware arc realizer.

Given a partition `owner` (cell -> region-id) where each region's clue cells all
share one value, find arcs the engine accepts that reproduce EXACTLY this
partition with each region scoring its clue value. Region area = its cell count
(enforced), smooth = value/area (checked by the engine at seal).

Sound: final acceptance is score_regions + clues_ok.
"""
import time, random
from collections import defaultdict
from regions import DSU, piece_on_edge
from backtrack import partial_components, is_open, smooth_by_root
from solver import score_regions, readout, clues_ok

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))
DIR_EDGE = {(0, 1): "R", (1, 0): "B", (0, -1): "L", (-1, 0): "T"}
OPP = {"R": "L", "L": "R", "T": "B", "B": "T"}
from regions import DISK_EDGES


def sliver_faces(arc_center, edge):
    if arc_center is None:
        return False
    return edge not in DISK_EDGES[arc_center]


def realize2(N, clues, green, owner, time_limit=10, seed=0):
    allcells = [(r, c) for r in range(N) for c in range(N)]
    # region id = owner value; derive value and size per region
    region_value = {}
    region_size = defaultdict(int)
    for cell in allcells:
        region_size[owner[cell]] += 1
    for cell, v in clues.items():
        rid = owner[cell]
        region_value[rid] = v   # all clue cells in a region share the value

    # cut edges from partition
    cut_by_pair = {}
    for r in range(N):
        for c in range(N):
            for (dr, dc) in ((0, 1), (1, 0)):
                nr, nc = r + dr, c + dc
                if nr < N and nc < N and owner[(r, c)] != owner[(nr, nc)]:
                    e = DIR_EDGE[(dr, dc)]
                    cut_by_pair[((r, c), (nr, nc))] = (e, OPP[e])

    rng = random.Random(seed)
    cluecells = set(clues)
    jitter = {cell: rng.random() for cell in allcells}
    assigned = set(); arcs = {}
    nbr = {cell: 0 for cell in allcells}
    sols = []; start = time.time(); st = {"nodes": 0, "to": False}

    def cut_ok(cell):
        r, c = cell
        for (dr, dc) in NB:
            nb = (r + dr, c + dc)
            if nb not in assigned:
                continue
            if (cell, nb) in cut_by_pair:
                eThis, eOther = cut_by_pair[(cell, nb)]
            elif (nb, cell) in cut_by_pair:
                eOther, eThis = cut_by_pair[(nb, cell)]
            else:
                continue
            if not (sliver_faces(arcs.get(cell), eThis) or sliver_faces(arcs.get(nb), eOther)):
                return False
        return True

    def closure():
        """region-aware: partition-consistency, area cap = region_size, integer
        area + no-dangling + exact smooth-score on closed clue regions."""
        dsu, comp = partial_components(N, arcs, assigned)
        # map component root -> set of owners of its labelled cells
        comp_owner = {}
        for cell in assigned:
            lp = (cell[0], cell[1], "W") if cell not in arcs else (cell[0], cell[1], "D")
            root = dsu.find(lp)
            o = owner[cell]
            if root in comp_owner:
                if comp_owner[root] != o:
                    return False
            else:
                comp_owner[root] = o
        # per-component tallies + closed check
        for root, ps in comp.items():
            full = sum(p[2] == "W" for p in ps)
            D = sum(p[2] == "D" for p in ps)
            S = sum(p[2] == "S" for p in ps)
            o = comp_owner.get(root)
            if o is not None and full + D > region_size[o]:
                return False
            closed = not any(is_open(N, arcs, assigned, p) for p in ps)
            if closed:
                if D != S:
                    return False
                for (r, c) in {(p[0], p[1]) for p in ps if p[2] in ("D", "S")}:
                    if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
                        return False
                if o is not None and full + D != region_size[o]:
                    return False
        # exact smooth on closed clue regions
        sm = None
        for root, ps in comp.items():
            o = comp_owner.get(root)
            if o is None or o not in region_value:
                continue
            if any(is_open(N, arcs, assigned, p) for p in ps):
                continue
            if sm is None:
                sm = smooth_by_root(N, arcs, dsu)
            full = sum(p[2] == "W" for p in ps); D = sum(p[2] == "D" for p in ps)
            if sm.get(root, 0) * (full + D) != region_value[o]:
                return False
        return True

    def pick():
        best = None; bk = None
        for cell in allcells:
            if cell in assigned: continue
            k = (nbr[cell], cell in cluecells, jitter[cell])
            if bk is None or k > bk: bk = k; best = cell
        return best

    def add(cell):
        assigned.add(cell); r, c = cell
        for dr, dc in NB:
            nb = (r+dr, c+dc)
            if nb in nbr: nbr[nb] += 1

    def rem(cell):
        assigned.discard(cell); r, c = cell
        for dr, dc in NB:
            nb = (r+dr, c+dc)
            if nb in nbr: nbr[nb] -= 1

    def rec(depth):
        if st["to"] or time.time() - start > time_limit:
            st["to"] = True; return True
        if depth == len(allcells):
            res = score_regions(N, dict(arcs))
            if res and clues_ok(res[0], clues):
                sols.append((dict(arcs), readout(N, res[0])))
                return True
            return False
        cell = pick()
        dom = (None,) if cell in green else (None, "TL", "TR", "BL", "BR")
        dom = list(dom); rng.shuffle(dom)
        for v in dom:
            st["nodes"] += 1
            add(cell)
            if v is not None: arcs[cell] = v
            if cut_ok(cell) and closure():
                if rec(depth + 1):
                    rem(cell); arcs.pop(cell, None); return True
            rem(cell); arcs.pop(cell, None)
        return False

    rec(0)
    return sols, st


if __name__ == "__main__":
    # Validate on 4x4 example (no merging, but per-region sizes).
    from regions import build_regions
    import input as data
    EX = {(0,0):'BL',(0,2):'BL',(1,0):'BR',(1,1):'BL',(1,2):'TL',(1,3):'TR',
          (2,0):'TR',(2,2):'TR',(3,1):'BL',(3,2):'BR'}
    N = 4; p = data.EXAMPLE
    reg = build_regions(N, EX)
    root_to_clue = {}
    for cc in p["clues"]:
        root_to_clue[reg["label_root"][cc]] = cc
    owner = {cell: root_to_clue[root] for cell, root in reg["label_root"].items()}
    sols, st = realize2(N, p["clues"], p["green"], owner, time_limit=20)
    print("example realize2:", [a for _, a in sols], "nodes", st["nodes"])
