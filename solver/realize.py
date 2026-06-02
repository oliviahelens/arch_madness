"""Given a Fillomino tiling (cell -> region seed), search for arcs that the
engine accepts with the correct clue scores. The tiling supplies CUT edges
(adjacent cells in different regions); a sound necessary condition is that every
CUT edge has a SLIVER facing it from at least one side. Final acceptance is the
engine (score_regions + clues_ok), so any returned config is correct.
"""
import time, random
from regions import DISK_EDGES
from pinned import closure_capped, AREA
from backtrack import partial_components
from solver import score_regions, readout, clues_ok

NB = ((0, 1), (1, 0), (0, -1), (-1, 0))
# opposite edge label for the neighbour direction, and the edge name from X's view
DIR_EDGE = {(0, 1): "R", (1, 0): "B", (0, -1): "L", (-1, 0): "T"}


def sliver_faces(arc_center, edge):
    """Does cell with this arc have its SLIVER on the given edge?"""
    if arc_center is None:
        return False            # whole cell: label on every edge
    return edge not in DISK_EDGES[arc_center]   # sliver = the two non-disk edges


def cut_edges_of(N, owner):
    cuts = []
    for r in range(N):
        for c in range(N):
            for (dr, dc) in ((0, 1), (1, 0)):
                nr, nc = r + dr, c + dc
                if nr < N and nc < N and owner[(r, c)] != owner[(nr, nc)]:
                    cuts.append(((r, c), (nr, nc), DIR_EDGE[(dr, dc)]))
    return cuts


def realize(N, clues, green, owner, time_limit=20, seed=0, area_cap=None):
    if area_cap is None:
        area_cap = {v: AREA[v] for v in set(clues.values())}
    allcells = [(r, c) for r in range(N) for c in range(N)]
    cuts = cut_edges_of(N, owner)
    # index cut edges by the two cells, with the edge label from each side
    OPP = {"R": "L", "L": "R", "T": "B", "B": "T"}
    cut_by_pair = {}
    for (a, b, eA) in cuts:
        cut_by_pair[(a, b)] = (eA, OPP[eA])

    # Precompute tight per-cell arc domains from the tiling.
    # arc at K allowed iff K's two edges are Same/border and the opposite two
    # are Cut/border (sound: disk never crosses a same-region join wrongly and
    # never sits on a cut; sliver sits only on cuts).
    CORNER = {"TL": ("T", "L"), "TR": ("T", "R"), "BL": ("B", "L"), "BR": ("B", "R")}
    OPP_C = {"TL": ("B", "R"), "TR": ("B", "L"), "BL": ("T", "R"), "BR": ("T", "L")}
    EDGE_D = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}

    def edge_class(cell):
        r, c = cell; cls = {}
        for e, (dr, dc) in EDGE_D.items():
            nb = (r + dr, c + dc)
            if not (0 <= nb[0] < N and 0 <= nb[1] < N):
                cls[e] = "brd"
            elif owner[nb] == owner[cell]:
                cls[e] = "S"
            else:
                cls[e] = "C"
        return cls

    domain = {}
    for cell in allcells:
        if cell in green:
            domain[cell] = (None,)
            continue
        # No SOUND local arc restriction exists beyond cut_ok (a disk may face a
        # cut if the neighbour slivers back; slivers may face a join if both
        # sliver). So keep the full domain; cut_ok + closure_capped do the work.
        domain[cell] = (None, "TL", "TR", "BL", "BR")

    rng = random.Random(seed)
    cluecells = set(clues)
    jitter = {cell: rng.random() for cell in allcells}
    assigned = set(); arcs = {}
    nbr = {cell: 0 for cell in allcells}
    sols = []; start = time.time(); st = {"nodes": 0, "to": False, "maxd": 0}

    def partition_consistent():
        """No component may contain labelled cells from two different tiling
        regions (that would merge regions the tiling says are distinct)."""
        dsu, comp = partial_components(N, arcs, assigned)
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
        return True

    def cut_ok(cell):
        """All CUT edges incident to `cell` whose other endpoint is also assigned
        must have a sliver facing from at least one side."""
        r, c = cell
        for (dr, dc) in NB:
            nb = (r + dr, c + dc)
            if nb not in assigned:
                continue
            pair = (cell, nb) if (cell, nb) in cut_by_pair else (
                (nb, cell) if (nb, cell) in cut_by_pair else None)
            if pair is None:
                continue
            eA, eB = cut_by_pair[pair]
            if pair[0] == cell:
                eThis, eOther = eA, eB
            else:
                eThis, eOther = eB, eA
            sf = sliver_faces(arcs.get(cell), eThis) or sliver_faces(arcs.get(nb), eOther)
            if not sf:
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
        st["maxd"] = max(st["maxd"], depth)
        if depth == len(allcells):
            res = score_regions(N, dict(arcs))
            if res and clues_ok(res[0], clues):
                sols.append((dict(arcs), readout(N, res[0])))
                return True
            return False
        cell = pick()
        dom = list(domain[cell]); rng.shuffle(dom)
        for v in dom:
            st["nodes"] += 1
            add(cell)
            if v is not None: arcs[cell] = v
            if (cut_ok(cell) and partition_consistent()
                    and closure_capped(N, arcs, assigned, clues, area_cap)):
                if rec(depth + 1):
                    rem(cell); arcs.pop(cell, None); return True
            rem(cell); arcs.pop(cell, None)
        return False

    rec(0)
    return sols, st


if __name__ == "__main__":
    # Validate on the 4x4 example: build its tiling from the known solution.
    from regions import build_regions
    import input as data
    EX = {(0,0):'BL',(0,2):'BL',(1,0):'BR',(1,1):'BL',(1,2):'TL',(1,3):'TR',
          (2,0):'TR',(2,2):'TR',(3,1):'BL',(3,2):'BR'}
    N = 4
    reg = build_regions(N, EX)
    # owner = map each cell to a representative clue cell of its region
    p = data.EXAMPLE
    root_to_clue = {}
    for cc in p["clues"]:
        lp = (cc[0], cc[1], "W") if cc not in EX else (cc[0], cc[1], "D")
        root_to_clue[reg["label_root"][cc]] = cc
    owner = {}
    ok = True
    for cell, root in reg["label_root"].items():
        if root in root_to_clue:
            owner[cell] = root_to_clue[root]
        else:
            ok = False
    print("all cells map to a clue region:", ok, "(unclued regions exist in example)")
    if ok:
        # example areas per clue value: 3->1, 9->3, 6->2, 8->4, 24->4
        ex_area = {3: 1, 9: 3, 6: 2, 8: 4, 24: 4}
        cap = {v: ex_area[v] for v in set(p["clues"].values())}
        sols, st = realize(N, p["clues"], p["green"], owner, time_limit=20, area_cap=cap)
        print("example realize answers:", [a for _, a in sols], "nodes", st["nodes"],
              "maxd", st["maxd"])
