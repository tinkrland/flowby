/**
 * selection.mjs: what a selection is, what it costs, and what may be done to it, without a DOM.
 *
 * read from fuser's canvas (docs/research.md, 2026-11-12): box-selecting two or more nodes floats a
 * pill at the bottom centre of the canvas holding focus, duplicate, delete, lock, then **the cost of
 * the selection**, then a "..." for the rest. the cost in the toolbar is the detail worth having:
 * a selection is a proposal, and a proposal's price belongs next to the hands that would spend it.
 *
 * flowby's unit is minutes, not fuser's credits, because minutes is what the compiler already sums
 * (`compile.cost`) and python now publishes per node. nothing here invents a number: a node without
 * `cost` contributes nothing, and a board whose nodes declare nothing says "cost unknown" rather
 * than showing a confident zero.
 */

/** the actions in the pill, in reading order: fuser's, minus the ones with nothing behind them. */
export const ACTIONS = Object.freeze(["focus", "duplicate", "delete", "lock"]);

/**
 * the selected nodes, in graph order, so the pill and the focus view never disagree about which came
 * first. ids that are not on the board are dropped: a stale id is not a node.
 * @param {string[]} ids
 * @param {any[]} nodes
 */
export function picked(ids, nodes) {
  const wanted = new Set(ids ?? []);
  return (nodes ?? []).filter((n) => wanted.has(n?.id));
}

/** one decimal, as a number, so a pill reads 5.4 min and 3 min and never 3.0 min */
function tidy(value) {
  return Math.round(value * 10) / 10;
}

/**
 * the minutes a set of nodes would cost, and how much of that is gpu time.
 *
 * `known` counts the nodes that declared a cost, because "0 min" from seven nodes that never said
 * and "0 min" from seven nodes that said zero are different facts, and one pill has room to be
 * right about only one of them.
 * @param {any[]} nodes
 */
export function costOf(nodes) {
  let minutes = 0;
  let gpu = 0;
  let known = 0;
  for (const node of nodes ?? []) {
    const cost = node?.cost;
    if (!cost || typeof cost.minutes !== "number") continue;
    known += 1;
    minutes += cost.minutes;
    if (cost.gpu) gpu += cost.minutes;
  }
  return { minutes: tidy(minutes), gpu: tidy(gpu), known };
}

/**
 * how the cost reads in the pill: how long, and whether it needs a gpu that may not be plugged in.
 * @param {{minutes: number, gpu: number, known: number}} cost
 */
export function costLabel(cost) {
  const n = cost ?? { minutes: 0, gpu: 0, known: 0 };
  if (!n.known) return { text: "cost unknown", hint: "no node in this selection declares a cost", timed: false, gpu: false };
  if (!n.minutes) return { text: "free", hint: "nothing in this selection takes machine time", timed: false, gpu: false };
  const text = `${n.minutes} min`;
  if (n.gpu > 0) {
    const share = n.gpu >= n.minutes ? "on a gpu throughout" : `${n.gpu} min on a gpu`;
    return { text, hint: share, timed: true, gpu: true };
  }
  return { text, hint: "on a cpu only", timed: true, gpu: false };
}

/** what control a value wants. anything exotic is shown, not edited. */
export function kindOf(value) {
  if (typeof value === "boolean") return "switch";
  if (typeof value === "number") return "number";
  if (value === null || value === undefined) return "empty";
  if (typeof value === "string") return "text";
  return "readonly";
}

/**
 * one node's parameters as fields for a focus view: a sentence you type, a number you nudge, a
 * switch you flip. the same filter the card uses (`nodeui.isTunable`), so a digest never becomes a
 * text box, and in the node's own key order, so a field does not move between openings.
 * @param {any} node
 * @param {(name: string, value: any) => boolean} [tunable]
 */
export function fieldsOf(node, tunable) {
  const params = node?.params ?? {};
  const fields = [];
  for (const [name, value] of Object.entries(params)) {
    if (tunable && !tunable(name, value)) continue;
    fields.push({ name, kind: kindOf(value), value });
  }
  return fields;
}

/**
 * the whole pill, as data. `enabled` is the truth about what the page can do to this selection, and
 * a disabled action carries its reason, so the tooltip is an answer rather than a shrug.
 * @param {string[]} ids
 * @param {any[]} nodes
 * @param {{locked?: string[], tunable?: (name: string, value: any) => boolean}} [options]
 */
export function pill(ids, nodes, options = {}) {
  const chosen = picked(ids, nodes);
  const count = chosen.length;
  const locked = new Set(options.locked ?? []);
  const allLocked = count > 0 && chosen.every((n) => locked.has(n.id));
  const cost = costOf(chosen);
  const first = chosen[0];
  return {
    visible: count > 0,
    count,
    word: `${count} node${count === 1 ? "" : "s"}`,
    // focus shows the selection as a form. it reads params, so one node is enough; several are a
    // chain, and the view then names it as the chain it is
    title: count === 1 ? String(first?.label || first?.op || first?.id || "node") : `${count} nodes`,
    actions: ACTIONS.map((name) => ({
      name,
      label: name === "lock" && allLocked ? "unlock" : name,
      enabled: count > 0,
      reason: count > 0 ? null : "nothing selected",
    })),
    cost: { ...cost, ...costLabel(cost) },
    fields: count === 1 ? fieldsOf(first, options.tunable) : [],
    chosen,
  };
}

/**
 * the "..." menu. fuser keeps its less common selection verbs there. flowby has exactly one worth
 * listing and it cannot work yet: a preset made from a selection needs somewhere to be stored, and
 * that store does not exist. it is listed, off, with the reason, rather than omitted and forgotten.
 */
export function moreMenu() {
  return [
    { name: "preset", label: "make a preset from these", enabled: false, reason: "there is no preset store yet" },
    { name: "copy", label: "copy their ids", enabled: true, reason: null },
  ];
}
