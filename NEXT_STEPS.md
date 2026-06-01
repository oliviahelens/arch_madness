# NEXT STEPS — read this first

## Experiment in one line
Does Claude (`claude-opus-4-8`) **discover** an unknown puzzle rule from a single
worked example (Arm A), vs. being **told** the rule (Arm B)? Novel Jane Street puzzle.
Sibling to `oliviahelens/CoGL_automaton`.

## Protocol decisions (locked)
- **Both, in order:** freeze Arm A blind → run it → THEN receive the verbal rule →
  build a deterministic solver + Arm B → compare.
- **Scoring:** only known ground truth is the worked example's answer = **18,928**
  (validates the solver). The 9×9 answer is unknown — scored by external submission,
  relayed manually. So the solver is our confidence source; treat submissions as scarce.
- Trials per arm: `NUM_TRIALS=8` (an answer distribution, not one sample).

## Sandbox rules — DO NOT VIOLATE
- **Do NOT search the web for the puzzle or its solution.** It's likely findable, but
  that spoils the induction test AND contaminates Arm A.
- **Arm A must never see the rule.** The verbal rule will live only in `src/rule.ts`
  (imported by Arm B + the solver, never by `src/prompts/armA.ts`). When the rule
  arrives, populate `ARM_A_FORBIDDEN` in `src/main.ts` with the rule text + key vocab
  so the leak guard aborts on any contamination.

## State as of last session
- ✅ Arm A pipeline built, typechecks clean.
- ✅ Images in `assets/` (`arch-madness_worked_example.jpg`, `arch-madness_input.jpg`),
  verified legible.
- ✅ Arm A frozen → `frozen/armA/payload.json` (two images + neutral text, no rule).
- ⏳ API key: added to the environment config by the user. A NEW session is needed for
  the container to have `ANTHROPIC_API_KEY`.
- ⏳ Arm B / `src/rule.ts` / solver: NOT built yet — await the rule (after Arm A runs).

## Command sequence for the new session
```bash
npm install          # fresh container — deps not committed
npm run check        # confirms the key can retrieve claude-opus-4-8 (404 = no access)
npm run freeze       # optional: re-print the exact Arm-A payload
npm run armA         # 8 trials; writes results/<ISO>/armA/ (answers, reasoning, usage)
```
Then report Arm A's answer distribution to the user and ask for the verbal rule to
proceed to the solver + Arm B.
