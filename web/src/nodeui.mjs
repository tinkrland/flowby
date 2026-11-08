/**
 * nodeui.mjs: what a node card shows, as decisions with no DOM.
 *
 * read from fuser's docs and clips (docs/research.md, 2026-11-08): a node is a card with a row per
 * property and a socket on each row, complexity is folded and not removed, the result is the body of
 * the card, an action bar appears under a selected node only, and the command bar lists every node
 * with its type signature so what it takes and gives is visible before it is added. this file holds
 * those rules. the React skin draws what it returns and decides nothing.
 *
 * what is borrowed is structure. fuser's own surfaces are pale with a dark toggle; flowby is dark
 * only, so nothing here names a colour except the four wire hues, which wires.mjs owns.
 */

import { wireFor } from "./wires.mjs";

// --- sockets ---------------------------------------------------------------------------------

/**
 * a socket's shape says how many connections it takes: a circle takes one, an oval takes many.
 * python already says which, per port, as `many`, so this reads it and invents nothing.
 */
export function socketShape(port) {
  return port.many ? "oval" : "circle";
}

/** the pixel box of a socket for a shape. an oval is a taller capsule, same width, so rows align. */
export const SOCKET = Object.freeze({ circle: { w: 9, h: 9 }, oval: { w: 9, h: 17 } });

// --- the card --------------------------------------------------------------------------------

/** parameters shown before the rest fold behind "N hidden". fuser shows the few that matter. */
export const VISIBLE_PARAMS = 3;

/**
 * how a param value reads on its row. the point is that a row is scannable: a number is trimmed, a
 * long string is cut, a boolean is words, and an object says what it holds and not its contents.
 */
export function formatValue(value) {
  if (value === null || value === undefined) return "none";
  if (typeof value === "boolean") return value ? "on" : "off";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(3)));
  if (typeof value === "string") return value.length > 22 ? `${value.slice(0, 21)}…` : value || "empty";
  if (Array.isArray(value)) return value.length ? `${value.length} item${value.length === 1 ? "" : "s"}` : "none";
  if (typeof value === "object") return `${Object.keys(value).length} fields`;
  return String(value);
}

/**
 * a param the user would tune, as opposed to one that identifies the node. asset digests and labels
 * are placement bookkeeping, and showing a sha256 as a property is noise.
 */
export function isTunable(name, value) {
  if (["asset", "text", "label", "deliverable"].includes(name)) return false;
  if (typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value)) return false;
  return true;
}

/**
 * the card for one node: its input rows, its tunable property rows (some folded), and its output
 * rows. rows keep a stable order, inputs then properties then outputs, so a card never reshuffles
 * when a value changes.
 */
export function cardOf(node, { expanded = false, visible = VISIBLE_PARAMS } = {}) {
  const inputs = Object.entries(node.inputs ?? {}).map(([name, port]) => row("in", name, port));
  const outputs = Object.entries(node.outputs ?? {}).map(([name, port]) => row("out", name, port));
  const tunables = Object.entries(node.params ?? {}).filter(([n, v]) => isTunable(n, v));
  const shown = expanded ? tunables : tunables.slice(0, visible);
  const properties = shown.map(([name, value]) => ({ side: "prop", name, value: formatValue(value), raw: value }));
  const hidden = expanded ? 0 : tunables.length - shown.length;
  return {
    id: node.id,
    title: node.label,
    kind: node.op,
    inputs,
    properties,
    hidden,
    foldLabel: hidden ? `${hidden} propert${hidden === 1 ? "y" : "ies"} hidden` : null,
    outputs,
    isElement: String(node.op ?? "").startsWith("element."),
  };
}

function row(side, name, port) {
  return {
    side, name, dtype: port.dtype, role: port.role ?? null,
    shape: socketShape(port), hex: wireFor(port.dtype).hex,
  };
}

/**
 * the height a card needs, so layout (dagre) and the drawn card agree. every row is the same height
 * and the fold line counts as one, because a layout that guesses is the thing graph.mjs exists to avoid.
 */
export const CARD = Object.freeze({ head: 40, row: 22, fold: 20, pad: 8, preview: 120, width: 232 });

export function cardHeight(card, { preview = false } = {}) {
  const rows = card.inputs.length + card.properties.length + card.outputs.length;
  return CARD.head + rows * CARD.row + (card.hidden ? CARD.fold : 0) + (preview ? CARD.preview : 0) + CARD.pad;
}

// --- running ---------------------------------------------------------------------------------

/**
 * which nodes can be run. an element is something placed and not something executed; everything
 * else is a step. the Execute pill is shown only when the selection holds a runnable node, which
 * is what fuser's toolbar does.
 */
export function runnable(node) {
  return !String(node.op ?? "").startsWith("element.");
}

export function executeState(selectedIds, nodesById) {
  const picked = selectedIds.map((id) => nodesById[id]).filter(Boolean);
  const steps = picked.filter(runnable);
  if (!steps.length) return { visible: false, label: null, count: 0 };
  return {
    visible: true, count: steps.length,
    label: steps.length === 1 ? `run ${steps[0].label}` : `run ${steps.length} steps`,
  };
}

/** the small bar under a selected node. which actions it offers depends on what the node is. */
export function actionsFor(node) {
  const base = [{ id: "properties", label: "properties" }, { id: "focus", label: "focus" }];
  if (node.op.startsWith("element.")) return [...base, { id: "replace", label: "replace" }, { id: "download", label: "download" }];
  return [...base, { id: "download", label: "download result" }, { id: "run", label: "run", primary: true }];
}

// --- the command bar -------------------------------------------------------------------------

/** a preset as a row: its name, what it takes, what it gives, and how long it is likely to take. */
export function commandRows(presets) {
  return presets.map((p) => ({
    id: p.name, label: p.label, blurb: p.blurb, stage: p.stage, state: p.state,
    signature: { from: p.from, to: p.to, chips: [chip(p.from), chip(p.to)] },
    models: p.models ?? [], estimate: p.estimate ?? null,
    appliesTo: p.applies_to ?? [],
    search: [p.name, p.label, p.blurb, p.from, p.to, p.stage, ...(p.applies_to ?? []), ...(p.models ?? [])].join(" ").toLowerCase(),
  }));
}

function chip(dtype) {
  const w = wireFor(dtype);
  return { dtype, label: { text: "TXT", image: "IMG", video: "VID", mesh: "3D" }[dtype] ?? dtype.toUpperCase(), hex: w.hex };
}

/**
 * search the command bar. every word must match somewhere (so "mesh sketch" narrows) and a match on
 * the label ranks above a match in the blurb. an empty query lists everything in stage order, so the
 * bar is useful before anything is typed.
 */
export function searchCommands(rows, query = "", { appliesTo = null } = {}) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const stageOrder = { explore: 0, refine: 1, output: 2 };
  let pool = rows;
  if (appliesTo) pool = pool.filter((r) => r.appliesTo.includes(appliesTo));
  const scored = [];
  for (const r of pool) {
    if (!words.every((w) => r.search.includes(w))) continue;
    let score = 0;
    for (const w of words) {
      if (r.label.toLowerCase().includes(w)) score += 3;
      if (r.id.includes(w)) score += 2;
      if (r.signature.from === w || r.signature.to === w) score += 2;
    }
    scored.push({ r, score });
  }
  scored.sort((a, b) => b.score - a.score || (stageOrder[a.r.stage] ?? 9) - (stageOrder[b.r.stage] ?? 9) || a.r.label.localeCompare(b.r.label));
  return scored.map((s) => s.r);
}

// --- quick connect ---------------------------------------------------------------------------

/**
 * drag from a socket to empty space and the menu lists what could be connected there. an output can
 * feed any preset that takes its dtype; an input can be fed by any preset that gives it. nothing
 * incompatible is offered, so every row is a wire that would be accepted.
 */
export function quickConnect(rows, { side, dtype, role = null }) {
  const key = side === "out" ? "from" : "to";
  const out = rows.filter((r) => r.signature[key] === dtype);
  return { side, dtype, role, options: out, empty: out.length === 0 ? `nothing takes ${dtype} here` : null };
}
