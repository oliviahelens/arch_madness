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
    "Solve the puzzle by these rules. Work carefully: place the arcs, determine the " +
    "regions and their integer areas, compute each region's score, fill every cell, " +
    "then compute the final answer. Manage your reasoning budget so you ALWAYS finish " +
    "with the answer line — even if uncertain, commit to your single best-guess integer. " +
    "End your response with the final answer on its own line, exactly in the form:\n" +
    "ANSWER: <integer>";

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
