import type Anthropic from "@anthropic-ai/sdk";
import { loadImage } from "../images.js";
import { ASSETS } from "../config.js";
import { RULE } from "../rule.js";

/**
 * ARM B — full prompt. Same two images as Arm A, PLUS the verbal rule.
 * This is the "told the rule" condition; no sandbox needed.
 */
export function buildArmB(): {
  system: string;
  messages: Anthropic.MessageParam[];
  texts: string[];
} {
  const worked = loadImage(ASSETS.workedExample);
  const newInput = loadImage(ASSETS.newInput);

  const system = "You are a careful, rigorous puzzle solver. Reason step by step.";

  const intro = "Here are the rules of the puzzle:";
  const labelWorked =
    "Here is a fully worked example (the starting grid, the same puzzle solved with arcs drawn, and the cells filled in with each region's score), ending in the example answer:";
  const labelNew = "Here is this month's puzzle for you to solve:";
  const instruction =
    "Solve the puzzle completely. Do the actual work — be systematic: refer to cells " +
    "by (row, column); decide arc placement cell by cell; trace the regions the arcs " +
    "create; verify each region's area is an integer (the quarter-disk pieces must " +
    "cancel); count each region's smooth perimeter pieces; compute every region's " +
    "score; check the scores match ALL numbered clues; then fill every cell with its " +
    "region's score and compute the final answer (sum of squares of row sums plus sum " +
    "of squares of column sums). Do NOT output a placeholder, round-number, or random " +
    "guess such as 1234567 — every digit of your answer must come from a grid you " +
    "actually worked out. If you cannot verify a unique solution, output the answer " +
    "implied by your best fully-worked-out grid. End with the final answer on its own " +
    "line, exactly in the form:\nANSWER: <integer>";

  const messages: Anthropic.MessageParam[] = [
    {
      role: "user",
      content: [
        { type: "text", text: `${intro}\n\n${RULE}` },
        { type: "text", text: labelWorked },
        { type: "image", source: { type: "base64", media_type: worked.mediaType, data: worked.data } },
        { type: "text", text: labelNew },
        { type: "image", source: { type: "base64", media_type: newInput.mediaType, data: newInput.data } },
        { type: "text", text: instruction },
      ],
    },
  ];

  return { system, messages, texts: [system, intro, RULE, labelWorked, labelNew, instruction] };
}
