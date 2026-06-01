import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const ROOT = path.resolve(__dirname, "..");
export const ASSETS_DIR = path.join(ROOT, "assets");
export const RESULTS_DIR = path.join(ROOT, "results");
export const FROZEN_DIR = path.join(ROOT, "frozen");

/** The model under test. Opus 4.8 (matches the latest Claude generation). */
export const MODEL = process.env.MODEL ?? "claude-opus-4-8";

/** Sampled trials per arm — a single instance needs repeats to get a pass rate. */
export const NUM_TRIALS = Number(process.env.NUM_TRIALS ?? 8);

/** Generous ceiling: this is a hard induction task and adaptive thinking eats budget.
 *  32k got fully consumed by reasoning before any answer; Opus 4.8 allows up to 128k
 *  with streaming. Stay high so the model can think AND still emit the answer line. */
export const MAX_TOKENS = Number(process.env.MAX_TOKENS ?? 64000);

/** Effort for a hard reasoning/induction task. high|xhigh are the sweet spots on Opus 4.8. */
export const EFFORT = (process.env.EFFORT ?? "high") as
  | "low"
  | "medium"
  | "high"
  | "xhigh"
  | "max";

export const ASSETS = {
  workedExample: "arch-madness_worked_example.jpg",
  newInput: "arch-madness_input.jpg",
} as const;
