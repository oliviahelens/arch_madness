"""Combinatorial region model (no geometry yet — that's perimeter.py).

A cell with an arc splits into:
  - 'D' disk piece (quarter circle, area pi/4 ~ 0.785, the MAJORITY piece -> labels the cell)
  - 'S' sliver piece (area 1 - pi/4 ~ 0.215, the minority piece)
A cell with no arc is one whole piece 'W' (area 1).

Arc centered at a corner: the disk touches the two edges meeting at that corner;
the sliver touches the two opposite edges. Pieces touching a shared grid edge from
each side are connected. Regions = connected components of pieces.

Identities for a VALID region (integer area):  #disk == #sliver, and
  area = (#whole) + (#disk) = number of cells the region labels.
"""

# arc center -> the two edges its DISK touches (T/B/L/R)
DISK_EDGES = {
    "TL": {"T", "L"},
    "TR": {"T", "R"},
    "BL": {"B", "L"},
    "BR": {"B", "R"},
}


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        root = x
        while self.p[root] != root:
            root = self.p[root]
        while self.p[x] != root:
            self.p[x], x = root, self.p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def piece_on_edge(arcs, r, c, edge):
    """Which piece of cell (r,c) touches its `edge` (one of T/B/L/R)."""
    ctr = arcs.get((r, c))
    if ctr is None:
        return (r, c, "W")
    return (r, c, "D") if edge in DISK_EDGES[ctr] else (r, c, "S")


def all_pieces(N, arcs):
    pieces = []
    for r in range(N):
        for c in range(N):
            if (r, c) in arcs:
                pieces.append((r, c, "D"))
                pieces.append((r, c, "S"))
            else:
                pieces.append((r, c, "W"))
    return pieces


def build_regions(N, arcs):
    """Return dict with:
        ok: bool (no dangling arcs AND every region has integer area)
        reason: str if not ok
        root_of: {piece: root}
        region_area: {root: int}
        label_root: {(r,c): root}   region that labels each cell
    """
    dsu = DSU()
    pieces = all_pieces(N, arcs)
    for p in pieces:
        dsu.find(p)

    for r in range(N):
        for c in range(N):
            if c + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "R"),
                          piece_on_edge(arcs, r, c + 1, "L"))
            if r + 1 < N:
                dsu.union(piece_on_edge(arcs, r, c, "B"),
                          piece_on_edge(arcs, r + 1, c, "T"))

    # No dangling: an arc's two pieces must be in different regions.
    for (r, c) in arcs:
        if dsu.find((r, c, "D")) == dsu.find((r, c, "S")):
            return {"ok": False, "reason": f"dangling arc at {(r, c)}"}

    # Per-region piece tallies.
    from collections import defaultdict
    full = defaultdict(int)
    disk = defaultdict(int)
    sliv = defaultdict(int)
    for p in pieces:
        root = dsu.find(p)
        if p[2] == "W":
            full[root] += 1
        elif p[2] == "D":
            disk[root] += 1
        else:
            sliv[root] += 1

    roots = set(dsu.find(p) for p in pieces)
    region_area = {}
    for root in roots:
        if disk[root] != sliv[root]:
            return {"ok": False, "reason": f"non-integer area region {root}"}
        region_area[root] = full[root] + disk[root]

    label_root = {}
    for r in range(N):
        for c in range(N):
            piece = (r, c, "W") if (r, c) not in arcs else (r, c, "D")
            label_root[(r, c)] = dsu.find(piece)

    return {
        "ok": True,
        "root_of": {p: dsu.find(p) for p in pieces},
        "region_area": region_area,
        "label_root": label_root,
    }
