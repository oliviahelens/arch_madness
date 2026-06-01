/**
 * Arm A must never see the verbal rule or the answer to the held-out instance.
 * This scans the human-readable text actually sent to the model (system + text
 * blocks — NOT the base64 image bytes, where a text match would be meaningless)
 * for any forbidden substring, and throws before the request can go out.
 *
 * `forbidden` is empty while Arm A is frozen blind. Once the rule arrives (for
 * Arm B), populate it with the rule text + key rule vocabulary so any accidental
 * contamination of the Arm-A payload aborts the run.
 */
export function assertNoLeak(texts: string[], forbidden: string[]): void {
  const haystack = texts.join("\n").toLowerCase();
  for (const term of forbidden) {
    const needle = term.trim().toLowerCase();
    if (needle.length >= 4 && haystack.includes(needle)) {
      throw new Error(
        `LEAK GUARD TRIPPED: forbidden term present in Arm A payload: ` +
          `"${term.slice(0, 60)}${term.length > 60 ? "…" : ""}"`,
      );
    }
  }
}
