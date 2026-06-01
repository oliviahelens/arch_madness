import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { MODEL, MAX_TOKENS, EFFORT, NUM_TRIALS, RESULTS_DIR } from "./config.js";
import { assertNoLeak } from "./leakguard.js";
import { extractInteger } from "./parse.js";

export type ArmBuild = {
  system: string;
  messages: Anthropic.MessageParam[];
  texts: string[];
};

function isoStamp(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function blockText(content: Anthropic.ContentBlock[]): { text: string; thinking: string } {
  let text = "";
  let thinking = "";
  for (const b of content) {
    if (b.type === "text") text += b.text;
    else if (b.type === "thinking") thinking += b.thinking;
  }
  return { text, thinking };
}

/**
 * Run one arm for NUM_TRIALS trials. Before each Arm-A call the leak guard scans
 * the outgoing text for `forbidden` terms. Every request payload and response is
 * written to results/<ISO>/<arm>/ so the "what did the model see" claim is auditable.
 */
export async function runArm(
  arm: string,
  build: () => ArmBuild,
  forbidden: string[] = [],
): Promise<void> {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error(
      "ANTHROPIC_API_KEY is not set in the environment — cannot call the API.",
    );
  }
  const client = new Anthropic();
  const outDir = path.join(RESULTS_DIR, isoStamp(), arm);
  const rawDir = path.join(outDir, "raw");
  fs.mkdirSync(rawDir, { recursive: true });

  const answers: (number | null)[] = [];

  for (let trial = 1; trial <= NUM_TRIALS; trial++) {
    const { system, messages, texts } = build();
    assertNoLeak(texts, forbidden);

    const request = {
      model: MODEL,
      max_tokens: MAX_TOKENS,
      thinking: { type: "adaptive" as const, display: "summarized" as const },
      output_config: { effort: EFFORT },
      system,
      messages,
    };

    // Record the exact text the model saw (images noted, base64 elided for size).
    fs.writeFileSync(
      path.join(rawDir, `${arm}-${trial}.request.json`),
      JSON.stringify(
        {
          ...request,
          messages: messages.map((m) => ({
            role: m.role,
            content: Array.isArray(m.content)
              ? m.content.map((c) =>
                  c.type === "image"
                    ? { type: "image", note: "<base64 elided>" }
                    : c,
                )
              : m.content,
          })),
        },
        null,
        2,
      ),
    );

    const stream = client.messages.stream(request);
    const final = await stream.finalMessage();
    const { text, thinking } = blockText(final.content);
    const answer = extractInteger(text);
    answers.push(answer);

    fs.writeFileSync(path.join(rawDir, `${arm}-${trial}.txt`), text);
    if (thinking) fs.writeFileSync(path.join(rawDir, `${arm}-${trial}.thinking.txt`), thinking);
    fs.writeFileSync(
      path.join(rawDir, `${arm}-${trial}.meta.json`),
      JSON.stringify(
        { answer, model: final.model, stop_reason: final.stop_reason, usage: final.usage },
        null,
        2,
      ),
    );

    console.log(`[${arm}] trial ${trial}/${NUM_TRIALS} -> ${answer ?? "PARSE_FAIL"}`);
  }

  const tally: Record<string, number> = {};
  for (const a of answers) tally[String(a)] = (tally[String(a)] ?? 0) + 1;
  const summary = { arm, model: MODEL, effort: EFFORT, trials: NUM_TRIALS, answers, tally };
  fs.writeFileSync(path.join(outDir, "summary.json"), JSON.stringify(summary, null, 2));
  console.log(`\n[${arm}] answer distribution:`, tally);
  console.log(`[${arm}] results -> ${outDir}`);
}
