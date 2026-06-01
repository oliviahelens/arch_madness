/**
 * The verbal rule for the puzzle. This is the ONLY place the rule lives.
 * It is imported by the Arm-B prompt builder and by the leak guard (to FORBID it
 * in Arm A). It is NOT imported by src/prompts/armA.ts.
 */
export const RULE = `Draw 90-degree arcs in some of the white cells. Arcs may not go in green cells. An arc has radius 1, connecting one corner of a cell to the opposite corner. (A cell may contain at most one arc.)

When finished, the arcs must divide the grid into regions, and those regions must have integer area. (Arcs are not allowed to "dangle" – that is, the two parts of a cell containing an arc must belong to distinct regions.)

For each region, compute the number of "smooth" (continuously differentible) pieces that comprise its perimeter. Multiply that number by the region's area to get its SCORE.

A cell labeled with a number indicates the score of the region that contains at least half (and possibly all) of that cell.

After completing the grid, fill each of the un-numbered cells with the score of the region that contains at least half of that cell. The answer to this month's puzzle is the sum of the squares of the row sums, plus the sum of the squares of the column sums. (As in the example.)`;

/** Substrings that must never appear in an Arm-A payload (the rule + its key vocab). */
export const FORBIDDEN_VOCAB = [
  RULE,
  "90-degree arc",
  "radius 1",
  "divide the grid into regions",
  "integer area",
  "dangle",
  "smooth",
  "continuously differen",
  "perimeter",
  "Multiply that number by the region",
  "sum of the squares of the row sums",
];
