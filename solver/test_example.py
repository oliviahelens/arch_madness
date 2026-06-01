"""Regression test: the engine must reproduce the published 4x4 example (18928).

These are the example's true arcs, hand-derived from the rule's edge-union logic
and confirmed by the engine (all six region scores + the answer match the image).
"""
from solver import score_regions, readout, clues_ok
import input as data

EXAMPLE_ARCS = {
    (0, 0): "BL", (0, 2): "BL",
    (1, 0): "BR", (1, 1): "BL", (1, 2): "TL", (1, 3): "TR",
    (2, 0): "TR", (2, 2): "TR",
    (3, 1): "BL", (3, 2): "BR",
}

if __name__ == "__main__":
    cs, info = score_regions(4, EXAMPLE_ARCS)
    assert clues_ok(cs, data.EXAMPLE["clues"]), "clue scores mismatch"
    ans = readout(4, cs)
    assert ans == data.EXAMPLE["answer"], f"answer {ans} != 18928"
    print("PASS: example reproduces", ans)
