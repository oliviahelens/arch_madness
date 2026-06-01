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

/** Ceiling, not a target — billed only for tokens actually generated, and the model
 *  isn't told its cap, so a high ceiling doesn't induce rambling; it just prevents
 *  cut-off. Set to the Opus 4.8 max (128k). Safe because we stream (no HTTP timeout).
 *  Caveat: a doomed/non-converging trial can now run all the way to 128k before stopping. */
export const MAX_TOKENS = Number(process.env.MAX_TOKENS ?? 128000);

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
