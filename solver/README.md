# Arch Madness solver (the "ground truth" / Arm-B side)

Deterministic engine + search for the Jane Street **Arch Madness** puzzle. The
engine is validated to reproduce the worked 4×4 example (**= 18,928**). The 9×9
puzzle's answer is, as of this writing, **not yet computationally extracted** —
see *Status & open problem* below.

> The verbal rule lives here (the solver side), not in the Arm-A blind pipeline.
> Arm A was frozen before any of this existed (`frozen/armA/payload.json`).

---

## The rule (as implemented by the engine)

Grid is `N×N`. Each **white** cell may hold one **arc** — a quarter-circle of
radius 1 centered at one of the cell's four corners (`TL/TR/BL/BR`) — or no arc.
**Green** cells never hold an arc.

An arc splits its cell into two pieces:
- **disk** `D` — the quarter-disk hugging the center corner (area `π/4 ≈ 0.785`,
  the **majority** piece; it is what "labels" the cell), and
- **sliver** `S` — the rest (area `1 − π/4 ≈ 0.215`, the minority piece).

A cell with no arc is a single **whole** piece `W`.

The disk touches the two cell edges meeting at its center corner; the sliver
touches the two opposite edges. **Pieces touching a shared grid edge from either
side are connected.** Regions are the connected components of pieces. (Interior
grid lines are *not* region boundaries — only arcs and the outer border are.)

A configuration is **valid** iff:
- **No dangling arc:** every arc's disk and sliver lie in *different* regions.
- **Integer area:** every region has `#disk == #sliver`, so its
  `area = #whole + #disk` is an integer (= the number of cells it labels).

**Score** of a region = `area × (number of smooth perimeter pieces)`, where a
"smooth piece" is a maximal `C¹` (no-corner) arc of the region's boundary. Arcs
are tangent to the cell edges at their endpoints, so an arc meeting a collinear
straight border (or another tangent arc) is a **smooth** join, while a 90°
straight/straight meeting is a **break**. A region with holes sums the smooth
counts of all its boundary cycles.

Each **clue** cell displays the score of the region that contains its majority
piece. (Distinct clue *values* may not share a region; equal values **may**.)

**Read-out / answer:** label every cell with its region's score, then
`answer = Σ_rows (row sum)² + Σ_cols (col sum)²`.

The 9×9 clues/greens are transcribed in `input.py` and were **verified against
`assets/arch-madness_input.jpg`** (all 18 clues + 20 greens match, including the
two clued-green cells (4,0)=25 and (8,5)=35).

---

## The engine (trusted core)

| file | role |
|---|---|
| `regions.py` | combinatorial region model (DSU over pieces; integer-area + no-dangling check) |
| `perimeter.py` | geometry: trace the arc/border arrangement into faces, count smooth (`C¹`) pieces |
| `solver.py` | `score_regions(N, arcs)` → per-cell scores (or `None` if invalid); `readout(...)` |
| `input.py` | the 4×4 example and the 9×9 puzzle (clues + greens) |
| `verify_solution.py` | **independently** re-check a `solution.json`: all clues + recomputed answer |

`score_regions` is the single source of truth: any candidate is only accepted
after it passes the engine **and** matches every clue.

```bash
python3 -c "import solver,input as d; print(solver.readout(4, solver.score_regions(4, {
 (0,0):'BL',(0,2):'BL',(1,0):'BR',(1,1):'BL',(1,2):'TL',(1,3):'TR',
 (2,0):'TR',(2,2):'TR',(3,1):'BL',(3,2):'BR'})[0]))"   # -> 18928
```

---

## Search attempts (none cracks the 9×9)

| file | approach | outcome |
|---|---|---|
| `backtrack.py` | row-major arc backtracking + frontier-closure pruning | solves 4×4; 9×9 reaches only ~depth 25/81 |
| `grow.py` | compact growth (assign the cell with most assigned neighbours) | 9×9 reaches ~depth 42, then walls |
| `region_grow.py`, `pinned.py`, `combined.py` | region-at-a-time / per-region area caps | 4×4 ok; 9×9 walls (caps were also unsound under merging) |
| `anneal.py`, `restarts.py` | simulated annealing / min-conflicts / breakout / random restarts | no traction (valid configs are rare, walls persist) |
| `fillomino.py` | partition the grid into connected polyomino regions (one clue each) | thousands of tilings; none realize (the connected, distinct-region model is wrong) |
| `fillomino2.py` | **merging-aware** tiling (equal-valued clues may share a region) + a **subset-sum feasibility** prune | sound & ~7× faster enumeration, but the space is astronomically large |
| `realize.py`, `realize2.py` | turn a fixed tiling into arcs, enforcing the partition + each region's exact `area×smooth=clue`, engine-verified at the leaf | correct (4×4 → 18928 in ~200 nodes), ~1 ms per tiling |
| `driver*.py` | parallel / work-stealing streaming of tilings → realizer | full CPU use; never reaches the solution |
| `shapecheck.py` | **sound per-shape realizability oracle** — `can_realize_shape(cells, N, smooth, green)`. A region's validity + smooth are determined by its own cells' arcs plus the sea cells forced to sliver into its label-edges; enumerating those is COMPLETE, so a False is a sound refutation. Localized to a small window; persistent cache (`shapecache.pkl`). | **works**: instant for size ≤4, ~1s size-5, ~secs size-7 (when realizable; refutation slower); size-9 too slow. Validated: all 6 ground-truth 4×4 regions return True. |
| `driver_oracle.py` | oracle-pruned tiling search + `realize2`, with persistent shape cache | prunes ~92% of small-region shapes; stalls on the same-value merge / area-budget interaction |
| `test_example.py`, `test_gen.py` | engine/pruning correctness tests on random valid grids | pass |

```bash
python3 verify_solution.py solution.json   # the path to a *verified* answer
python3 realize2.py                         # 4×4 sanity (-> 18928)
python3 driver_mp3.py 600 4 4 128           # merging tiling search (won't finish)
```

---

## Key findings (the puzzle's structure)

- `Σ region areas = N² = 81` always (each arc contributes 1 disk to its region).
- For a clue `v`, `area | v` and `smooth = v/area`. Smooth values are smallish
  but rise with size (4×4 data: area-3 reaches smooth 7; area-5 reaches 11).
- **Equal-valued clues can share a region.** This defeats the clean
  "18 distinct minimal-area regions summing to 81" pinning that first looked so
  promising — e.g. the three 27-clues plausibly form *one* area-9/smooth-3 region
  rather than three area-3/smooth-9 regions.
- A region's **labelled cells can be disconnected** (bridged by slivers): ~47% of
  random valid configs have at least one such region. So a connected-polyomino
  tiling model is not guaranteed to contain the solution.
- A region's validity (integer area, no-dangling) and its smooth count are fully
  determined by the arcs on the region's cells + the sea cells forced to sliver
  into its label-edges — **local**, which makes the `shapecheck.py` oracle *sound*
  and (after localization) fast enough for size ≤6.

### Oracle-derived deductions (sound)
- **size-3 regions can only reach smooth {3, 5}, and only at a border** (interior
  small regions can't balance #disk = #sliver — borders remove edges that would
  otherwise each force an inward sliver). Hence:
  - clue 21 (=3×7) cannot be size 3 → **size 7, smooth 3**;
  - clue 27 (=3×9) cannot be size 3 → **size 9, smooth 3**.
- size-5 reaches smooth up to 9 (e.g. a U-pentomino at a corner), but again only
  at the border; ~**92 % of small connected shapes are unrealizable** for the
  smooth their clue requires.
- Consequence: small clue regions must hug the grid border; interior clues' regions
  must extend to a border or be large.

---

## Status & open problem

The **engine is trusted** (reproduces 18,928). The **9×9 answer is not extracted**,
but the `shapecheck.py` oracle added a genuinely new, sound pruning/deduction
capability (see *Oracle-derived deductions*).

**Current precise blocker (post-oracle):** with oracle pruning, the connected
tiling search reaches ~13/17 regions but stalls on the same-value **merge /
area-budget** interaction. Total region area must be 81; the three 27-clues placed
as *separate* size-9 regions consume 27 cells and leave no room for 45/63/288, so
they are *forced* to merge into one size-9 region — but the depth-first search
explores the (astronomically many) non-merged size-9 shapes first. The size-7/9
oracle is too slow to prune those large regions. The most promising next step is to
**enumerate the feasible same-value groupings + sizes up front** (a small
combinatorial problem fixed by the area budget), then grow + oracle-prune + realize
each — instead of discovering merges by blind backtracking.

Older framing (still relevant):

Why it's hard: the real solution space is either the arcs (`~5^61`, no clean
constraint propagation) or the merged-region tilings (astronomically many, and
`realize2` can only reject a tiling *after* it's fully built). The crux is that
the **smooth-count is a geometric black box** — non-local enough that no
SAT/CP-style propagation prunes the search, yet the space is far too large to
enumerate. The one lever that could collapse it (per-shape realizability
pruning, `shapecheck.py`) can't be both **sound** and **fast**: the fast
structural version is wrong (cells legitimately sliver toward each other to make
high-smooth boundaries), and the sound general version times out on exactly the
large regions (size 7–9) that drive the explosion.

**The reliable way to get a verified answer:** drop the solved grid's arcs into
`solution.json` as `{"answer": <n>, "arcs": {"r,c": "TL|TR|BL|BR", ...}}` (omit
whole cells) and run `python3 verify_solution.py` — it re-derives every region
through the engine, checks all 18 clues, and recomputes the read-out.

### If continuing the search
- A smarter *human-style* deduction (forced arcs near greens/edges/corners) that
  this code never found.
- A genuine smooth-count-aware propagation model (hard: needs the geometry
  encoded, not black-boxed).
- Relaxing the connectivity assumption in `realize2`/`fillomino2` to admit
  disconnected labelled regions (larger space, but closes the soundness gap).
