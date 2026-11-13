/**
 * inspector.mjs: what the contextual panel shows for a node, without a DOM.
 *
 * this is the surface per-node history was built for. python files a run under a signature and can say
 * what a run would reuse (`inspector.mjs`'s payload comes from `bin/flowby --json inspector`); the panel
 * is the place a person reads that, so a node that has never run must look like a node that has never
 * run rather than like a node with nothing to say.
 *
 * three rules the module keeps, because they are the ones a panel usually breaks:
 *
 * 1. **a count is a fact, not a decoration.** "3 runs" is printed from the length of a list; nothing
 *    here rounds an empty history into "0 runs" and calls it a state. a node with no runs says so.
 * 2. **stale is a question about now.** the verdict comes from python, computed against the node's
 *    current signature. this module never recomputes it from params, because two implementations of
 *    "has this changed" would disagree and the panel would be the wrong one.
 * 3. **minutes are what the node costs, not what it spent.** the history says what a run spent; the
 *    header says what running it again would cost. conflating them makes a re-run look free.
 */

/** a run's age, in the coarsest unit that still says something. */
export function age(at, now = Date.now() / 1000) {
  if (!Number.isFinite(at) || at <= 0) return "unknown";
  const seconds = Math.max(0, now - at);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/** one decimal at most, and never a false precision: 0.4 stays 0.4, 3 stays 3. */
function minutes(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "0";
  return String(Math.round(n * 10) / 10);
}

/**
 * the history rows for one node, newest first.
 *
 * a failed run is shown, and is not dressed as a success: the row carries its own state so the panel
 * can put the dot in the wrong colour. hiding failures is how a history stops being worth reading.
 * @param {{runs?: any[]}} node
 * @param {number} now
 */
export function history(node, now = Date.now() / 1000) {
  // newest first is the panel's rule, not the payload's. two callers already disagree: the inspector
  // export reverses and `Book.as_dict` does not, so sorting here is what keeps the promise true.
  const ordered = [...(node?.runs ?? [])].sort((a, b) => (Number(b?.at) || 0) - (Number(a?.at) || 0));
  return ordered.map((run) => ({
    id: String(run?.id ?? ""),
    state: run?.state === "ok" ? "ok" : "failed",
    spent: minutes(run?.minutes),
    at: age(run?.at, now),
    note: typeof run?.note === "string" ? run.note : "",
    artifacts: Array.isArray(run?.artifacts) ? run.artifacts.length : 0,
  }));
}

/**
 * the panel for one node: its header, its history, and what a run of it would do.
 *
 * `work` is the board's answer, so the panel does not have to decide what "reuse" means. an unknown
 * node returns null rather than an empty panel, and the board shows nothing.
 * @param {string} id
 * @param {{nodes?: Record<string, any>, work?: any}} doc
 * @param {number} now
 */
export function panel(id, doc, now = Date.now() / 1000) {
  const node = doc?.nodes?.[id];
  if (!node) return null;
  const rows = history(node, now);
  const verdict = node.verdict === "reuse" ? "reuse" : "run";
  const last = rows[0] ?? null;
  return {
    id: node.id ?? id,
    title: node.label || node.op || id,
    op: node.op ?? "",
    params: Object.entries(node.params ?? {}).map(([name, value]) => ({
      name, value: typeof value === "number" ? String(Math.round(value * 1000) / 1000) : String(value),
    })),
    cost: {
      value: minutes(node.minutes),
      gpu: Boolean(node.gpu),
      label: node.gpu ? "gpu minutes" : "minutes",
    },
    rows,
    count: rows.length,
    empty: rows.length === 0,
    emptyLine: "never run. a first run costs what the header says.",
    // the verdict is python's, and the panel repeats it with python's own reason when there is one
    verdict,
    verdictLine: verdict === "reuse"
      ? (last ? `reuse the run from ${last.at} (${last.spent} min)` : "reuse the last run")
      : (node.because ? `run: ${node.because}` : "run: nothing has run this signature"),
    cancelled: rows.filter((r) => r.state === "failed").length,
  };
}

/**
 * the board's line: what the next run would execute, and what it would stand on.
 *
 * this is the fact the whole module exists for. "run 7 nodes" and "run 0, reuse 7" are different
 * sentences, and the board should say the second one when it is true.
 * @param {{work?: any, nodes?: Record<string, any>}} doc
 */
export function summary(doc) {
  const work = doc?.work ?? {};
  const run = Array.isArray(work.run) ? work.run.length : 0;
  const reuse = Array.isArray(work.reuse) ? work.reuse.length : 0;
  const spent = minutes(work.minutes);
  if (!run && !reuse) return { run, reuse, spent, line: "nothing on this board to run" };
  if (!run) return { run, reuse, spent, line: `nothing to run: all ${reuse} nodes reuse a run` };
  return {
    run, reuse, spent,
    line: `${run} to run (${spent} min), ${reuse} reused`,
  };
}
