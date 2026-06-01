# Image assets

Drop the puzzle images here with these exact filenames:

- `worked_example.png` — the single worked example: the starting grid, the same
  puzzle solved (with curves), and its final integer answer ("example answer = ...").
- `new_input.png` — the new puzzle grid to solve (the 9×9).

Both arms receive **both** images. The only thing that differs between arms is the
**verbal rule text** (Arm B only) — see `src/rule.ts` (added after Arm A is frozen).

Send images at full resolution; Opus 4.8 supports high-res vision, and the grids
need to be legible (small digits, thin curves).
