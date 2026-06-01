import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { buildArmA } from "./prompts/armA.js";
import { buildArmB } from "./prompts/armB.js";
import { runArm } from "./run.js";
import { assertNoLeak } from "./leakguard.js";
import { FROZEN_DIR, MODEL } from "./config.js";
import { FORBIDDEN_VOCAB } from "./rule.js";
import { readoutAnswer, EXAMPLE_FILLED, EXAMPLE_ANSWER } from "./readout.js";

/** Arm A must never contain the rule or its key vocabulary. */
const ARM_A_FORBIDDEN: string[] = FORBIDDEN_VOCAB;

async function main() {
  const cmd = process.argv[2] ?? "armA";

  if (cmd === "validate") {
    // Machine-check the read-out function against the published example.
    const got = readoutAnswer(EXAMPLE_FILLED);
    const ok = got === EXAMPLE_ANSWER;
    console.log(`read-out(example) = ${got}  expected ${EXAMPLE_ANSWER}  -> ${ok ? "PASS" : "FAIL"}`);
    if (!ok) process.exit(1);
    return;
  }

  if (cmd === "check") {
    // Confirm the key can actually retrieve the target model (4.8, not 4.7).
    // A 404 here means the account lacks access — the API never silently downgrades.
    if (!process.env.ANTHROPIC_API_KEY) throw new Error("ANTHROPIC_API_KEY is not set.");
    const client = new Anthropic();
    const m = await client.models.retrieve(MODEL);
    console.log(`Model access confirmed: id=${m.id} display_name=${m.display_name}`);
    return;
  }

  if (cmd === "freeze") {
    // Build the Arm-A payload, run the leak guard, and write the frozen text
    // record WITHOUT calling the API — the auditable "what Arm A sees" snapshot.
    const { system, messages, texts } = buildArmA();
    assertNoLeak(texts, ARM_A_FORBIDDEN);
    fs.mkdirSync(path.join(FROZEN_DIR, "armA"), { recursive: true });
    fs.writeFileSync(
      path.join(FROZEN_DIR, "armA", "payload.json"),
      JSON.stringify(
        {
          system,
          texts,
          messages: messages.map((m) => ({
            role: m.role,
            content: Array.isArray(m.content)
              ? m.content.map((c) => (c.type === "image" ? { type: "image", note: "<base64 elided>" } : c))
              : m.content,
          })),
        },
        null,
        2,
      ),
    );
    console.log("Arm A payload frozen -> frozen/armA/payload.json");
    console.log("Text the model will see:\n");
    console.log(texts.join("\n---\n"));
    return;
  }

  if (cmd === "armA") {
    await runArm("armA", buildArmA, ARM_A_FORBIDDEN);
    return;
  }

  if (cmd === "armB") {
    await runArm("armB", buildArmB, []); // Arm B is the full-prompt arm; no forbidden terms.
    return;
  }

  throw new Error(`Unknown command: ${cmd} (use: validate | check | freeze | armA | armB)`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
