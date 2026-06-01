/**
 * The puzzle's read-out / scoring step (the deterministic, verifiable part).
 *
 * Given a completed grid where every cell holds its region's SCORE, the answer is
 * the sum of the squares of the row sums plus the sum of the squares of the column
 * sums. Validated against the published example (filled grid -> 18,928).
 */
export function readoutAnswer(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const rowSums = grid.map((r) => r.reduce((a, b) => a + b, 0));
  const colSums: number[] = [];
  for (let c = 0; c < cols; c++) {
    let s = 0;
    for (let r = 0; r < rows; r++) s += grid[r][c];
    colSums.push(s);
  }
  const sq = (x: number) => x * x;
  const rowPart = rowSums.reduce((a, s) => a + sq(s), 0);
  const colPart = colSums.reduce((a, s) => a + sq(s), 0);
  return rowPart + colPart;
}

/** The example's completed grid (every cell = its region SCORE), from the puzzle image. */
export const EXAMPLE_FILLED: number[][] = [
  [3, 9, 9, 6],
  [8, 8, 9, 6],
  [8, 8, 24, 24],
  [6, 6, 24, 24],
];

export const EXAMPLE_ANSWER = 18928;
