/**
 * rail.mjs: the left rail, and the nodes popover, decided without a DOM.
 *
 * the rail is the board's primary control (owner, 2026-11-13, from FLORA's board): five slots in a
 * fixed order, a divider, then the one action that is not always available, run. so this file owns the
 * three things a component would otherwise invent for itself: the order, when a slot is live, and the
 * sentence a slot says when it is not.
 *
 * it also owns the popover's grouping. grouping by **output type** rather than by model family is the
 * honest axis here: presets.json declares `from` and `to` for every preset, and dtypes.py is the
 * source of truth for which types exist. a group nothing writes cannot appear.
 */

import { WIRES } from "./wires.mjs";

/** the five slots, in the order the reference board shows them. */
export const RAIL = Object.freeze([
  { id: "add", icon: "plus", label: "add", hint: "a frame, a file, or a frame from figma" },
  { id: "library", icon: "library", label: "library", hint: "preset kits: styles, subtypes and presets" },
  { id: "command", icon: "command", label: "command", hint: "every preset, with the types it reads and writes" },
  { id: "nodes", icon: "nodes", label: "nodes", hint: "discover nodes and connect them", key: "shift+a" },
  { id: "settings", icon: "settings", label: "settings", hint: "the gpu you rent, and what is plugged in" },
]);

export const RUN = Object.freeze({ id: "run", icon: "run", label: "run", hint: "run what is selected" });

/** stages in the order a person works in, not alphabetically. */
const STAGE_ORDER = ["explore", "refine", "output"];

const NARROW_WHY = "the board is an editor on a desktop; this page is the phone view";

/**
 * slots whose panel still lives somewhere else.
 *
 * a rail slot that opened nothing would be a button that lies, so a slot listed here is drawn dim with
 * the reason in its tooltip. empty since 2026-11-13: library and settings moved out of the header into
 * their slots, so every slot now opens something. the mechanism stays, because the next panel built
 * for the header will need the same honesty.
 */
export const PENDING = Object.freeze({});

/**
 * the rail, with liveness.
 *
 * `on` is whether the slot does anything; `why` is what it says when it cannot. a dead slot keeps its
 * place, because a rail whose items move is worse than a rail with one dim item.
 *
 * @param {{hasSelection?: boolean, narrow?: boolean}} state
 */
export function railState(state = {}) {
  const hasSelection = Boolean(state?.hasSelection);
  const narrow = Boolean(state?.narrow);
  const items = RAIL.map((slot) => {
    if (narrow) return { ...slot, on: false, why: NARROW_WHY };
    const pending = PENDING[slot.id];
    return { ...slot, on: !pending, why: pending ?? null };
  });
  const run = {
    ...RUN,
    on: hasSelection && !narrow,
    why: narrow ? NARROW_WHY : hasSelection ? null : "select a node first: a run has nothing to act on until there is a selection",
  };
  return { items, run, visible: !narrow };
}

/**
 * presets grouped by the type they write, for the nodes popover.
 *
 * @param {any[]} presets rows from presets.json
 */
export function nodeGroups(presets) {
  const list = (presets ?? []).filter((p) => p && typeof p === "object");
  const byType = new Map();
  for (const wire of WIRES) byType.set(wire.dtype, { dtype: wire.dtype, hex: wire.hex, means: wire.means, rows: [] });
  const other = { dtype: "other", hex: "#71717a", means: "not declared", rows: [] };
  for (const preset of list) {
    const group = byType.get(preset.to) ?? other;
    group.rows.push({
      name: preset.name,
      label: preset.label ?? preset.name,
      blurb: preset.blurb ?? "",
      from: preset.from ?? null,
      to: preset.to ?? null,
      stage: preset.stage ?? "explore",
      estimate: typeof preset.estimate === "number" ? preset.estimate : null,
      variants: Number.isFinite(preset.variants) ? preset.variants : 1,
      variantNoun: typeof preset.variant_noun === "string" ? preset.variant_noun : null,
    });
  }
  // vectary's picker says how many things a card makes ("16 design variations"), and that is the one
  // piece of its naming worth copying: a card whose name does not say "four" is a card a person runs
  // four times by hand and then wonders why.
  for (const group of [...byType.values(), other]) {
    for (const row of group.rows) row.show = countedName(row);
  }
  const rank = (stage) => {
    const at = STAGE_ORDER.indexOf(stage);
    return at === -1 ? STAGE_ORDER.length : at;
  };
  const groups = [...byType.values(), other]
    .filter((g) => g.rows.length > 0)
    .map((g) => ({
      ...g,
      rows: g.rows.slice().sort((a, b) => rank(a.stage) - rank(b.stage) || a.label.localeCompare(b.label)),
      count: g.rows.length,
    }));
  return { groups, total: list.length, empty: "no preset writes that type yet" };
}

/** what a wire carries, said as the thing a card makes. counts come before the noun, as vectary does it. */
const NOUNS = Object.freeze({ image: "images", video: "clips", mesh: "meshes", text: "captions" });

/**
 * the name a person reads. one variant is the label, because "1 image" is noise; more than one counts
 * itself, because four takes on one frame is the reason to press the card at all.
 *
 * @param {{ label?: string, variants?: number, to?: string|null, show?: string }} row
 */
export function countedName(row) {
  const variants = Number.isFinite(row?.variants) ? row.variants : 1;
  if (variants <= 1) return row?.label ?? "";
  // a declared noun wins, because "6 meshes" is wrong for a card that makes six materials
  const noun = row?.variantNoun ?? NOUNS[row?.to] ?? "results";
  return `${variants} ${noun}`;
}

/**
 * a preset's estimate, in words. the same rule as everywhere else: a missing number is unknown, never
 * zero, and nothing is rounded into a claim it did not make.
 *
 * @param {number|null|undefined} minutes
 */
export function estimateText(minutes) {
  if (minutes === null || minutes === undefined || !Number.isFinite(minutes)) return "cost unknown";
  if (minutes === 0) return "free";
  return `${minutes % 1 === 0 ? minutes : minutes.toFixed(1)} min`;
}
