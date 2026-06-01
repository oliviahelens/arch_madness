import fs from "node:fs";
import path from "node:path";
import { buildArmA } from "./prompts/armA.js";
import { runArm } from "./run.js";
import { assertNoLeak } from "./leakguard.js";
import { FROZEN_DIR } from "./config.js";

/**
 * Arm A forbidden-terms list. EMPTY while Arm A is frozen blind.
 * After the verbal rule arrives (for Arm B), populate this with the rule text and
 * key rule vocabulary so any contamination of the Arm-A payload aborts the run.
 */
const ARM_A_FORBIDDEN: string[] = [];

async function main() {
  const cmd = process.argv[2] ?? "armA";

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
    throw new Error(
      "Arm B is not built yet — it awaits the verbal rule. Once provided, " +
        "src/rule.ts + src/prompts/armB.ts will be added and ARM_A_FORBIDDEN populated.",
    );
  }

  throw new Error(`Unknown command: ${cmd} (use: freeze | armA | armB)`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
