import type Anthropic from "@anthropic-ai/sdk";
import { loadImage } from "../images.js";
import { ASSETS } from "../config.js";

/**
 * ARM A — induction from a single worked example.
 *
 * The payload contains ONLY: the worked example image, the new-input image, and
 * deliberately neutral instructions. It does NOT import or reference the verbal
 * rule (that lives in src/rule.ts, imported only by Arm B). The labels below
 * describe what the images literally show — they do not state the rule.
 */
export function buildArmA(): {
  system: string;
  messages: Anthropic.MessageParam[];
  texts: string[];
} {
  const worked = loadImage(ASSETS.workedExample);
  const newInput = loadImage(ASSETS.newInput);

  const system =
    "You are a careful, rigorous puzzle solver. Reason step by step.";

  const labelWorked =
    "Here is one fully worked example of a puzzle: the starting grid, the same " +
    "puzzle solved, and its final answer (a single integer).";
  const labelNew = "Here is a new puzzle of the same kind for you to solve:";
  const instruction =
    "Study the worked example and infer how the puzzle works, then solve the " +
    "new puzzle. Show your reasoning, but manage your reasoning budget so that " +
    "you ALWAYS finish with the answer line — even if you are not fully certain, " +
    "commit to your single best-guess integer rather than leaving it blank. End " +
    "your response with the final answer on its own line, exactly in the form:\n" +
    "ANSWER: <integer>";

  const messages: Anthropic.MessageParam[] = [
    {
      role: "user",
      content: [
        { type: "text", text: labelWorked },
        {
          type: "image",
          source: { type: "base64", media_type: worked.mediaType, data: worked.data },
        },
        { type: "text", text: labelNew },
        {
          type: "image",
          source: { type: "base64", media_type: newInput.mediaType, data: newInput.data },
        },
        { type: "text", text: instruction },
      ],
    },
  ];

  return {
    system,
    messages,
    texts: [system, labelWorked, labelNew, instruction],
  };
}
