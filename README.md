# arch_madness — induction-vs-instruction on a novel puzzle

A sibling experiment to [`CoGL_automaton`](https://github.com/oliviahelens/CoGL_automaton).
Where CoGL tested whether the model could *execute* a known rule (Conway's Game of
Life) via in-context reasoning, this tests whether it can **discover** an unknown
rule and apply it — on a novel (Jane Street) puzzle.

## The two arms

Both arms see the **same** images: one fully worked example (start grid → solved →
final integer answer) and a new puzzle to solve. They differ by exactly one thing —
the **verbal rule text**:

| | Arm A (induction) | Arm B (full prompt) |
|---|---|---|
| worked example image | ✅ | ✅ |
| new-input image | ✅ | ✅ |
| **verbal rule (text)** | ❌ withheld | ✅ |

Arm A must infer the method from a single worked example. Arm B is told the rule
in words.

## Scoring

The only ground truth we hold is the worked example's answer (**18,928**), used to
validate the deterministic solver. The new puzzle's answer is unknown — it is scored
by external submission (relayed manually). Each arm runs `NUM_TRIALS` sampled trials
to get an answer distribution rather than a single sample.

## No-leak guarantee (Arm A sandbox)

- The verbal rule lives only in `src/rule.ts`, imported solely by the Arm-B builder
  and the oracle — `src/prompts/armA.ts` cannot reference it.
- `src/leakguard.ts` scans the human-readable text of every Arm-A payload for
  forbidden substrings (the rule text + key vocabulary) and aborts on any match.
- Every request payload is written to `results/<ISO>/<arm>/raw/*.request.json`
  (base64 image bytes elided), so "Arm A never saw the rule" is auditable, not just
  asserted. `npm run freeze` writes the snapshot without calling the API.

## Status

- ✅ Arm A pipeline (blind: images + neutral instructions only); frozen to
  `frozen/armA/payload.json`.
- ✅ Images in `assets/` (`arch-madness_worked_example.jpg`, `arch-madness_input.jpg`).
- ⏳ Set `ANTHROPIC_API_KEY` in the environment, then run Arm A.
- ✅ **Deterministic engine built** in `solver/` (Python) — implements the rule and
  **reproduces the worked example = 18,928**. See **[`solver/README.md`](solver/README.md)**
  for the rule write-up, every search approach tried, and findings.
  - ⚠️ The 9×9 puzzle answer is **not yet computationally extracted** (search space too
    large; the smooth-count is a geometric black box that blocks propagation). The
    dependable path to a *verified* number is `solver/verify_solution.py` on a solved
    arc grid.
- ⏳ TS Arm-B builder (`src/rule.ts`, `src/prompts/armB.ts`) + Arm-A leak-guard list:
  not built yet.

## Run

```bash
npm install
npm run freeze   # build + leak-check + snapshot the Arm-A payload (no API call)
npm run armA     # run Arm A for NUM_TRIALS trials
```

Config via env: `MODEL` (default `claude-opus-4-8`), `NUM_TRIALS` (8), `EFFORT`
(`high`), `MAX_TOKENS` (32000).
