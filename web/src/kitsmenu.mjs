/**
 * kitsmenu.mjs: what the preset kits menu shows, decided without a DOM.
 *
 * python owns each member's true state (kits.py: listed, corpus, training, ready) and whether it
 * can run. this file only arranges that for reading, and its one rule mirrors the plug's: a member
 * is offered as usable only when python said `runnable`. a listed style is a name on a list, and
 * the menu says so in its own word instead of looking like a button.
 */

export const STATE_WORD = Object.freeze({
  listed: "listed, not built yet",
  corpus: "gathering images",
  training: "training",
  ready: "ready",
});

/** an unknown state reads as listed: the weakest claim, never a stronger one */
export function wordFor(state) {
  return STATE_WORD[state] ?? STATE_WORD.listed;
}

/** members in reading order: a parent, then its subtypes indented under it, others in given order */
export function ordered(members) {
  const list = members ?? [];
  const ids = new Set(list.map((m) => m.id));
  const kids = new Map();
  for (const m of list) {
    if (m.parent && ids.has(m.parent)) kids.set(m.parent, [...(kids.get(m.parent) ?? []), m]);
  }
  const out = [];
  for (const m of list) {
    if (m.parent && ids.has(m.parent)) continue;      // placed under its parent below
    out.push({ ...m, depth: 0 });
    for (const k of kids.get(m.id) ?? []) out.push({ ...k, depth: 1 });
  }
  return out;
}

/** one kit as rows. `ready` and `total` are counted here from the members, not trusted from a header. */
export function kitView(kit) {
  const members = ordered(kit.members);
  const ready = members.filter((m) => m.runnable === true && m.state === "ready").length;
  return {
    id: kit.id,
    label: kit.label,
    blurb: kit.blurb,
    ready,
    total: members.length,
    summary: `${ready} of ${members.length} ready`,
    rows: members.map((m) => ({
      id: m.id,
      label: m.label,
      blurb: m.blurb,
      depth: m.depth,
      state: m.state,
      word: wordFor(m.state),
      // usable only when python says so AND the state agrees; anything else is a name on a list
      usable: m.runnable === true && m.state === "ready",
    })),
  };
}

/** the header button: it says how many members can really run, never how many exist */
export function kitsButton(kits, { reachable = true } = {}) {
  if (!reachable) return { label: "preset kits", tone: "off", title: "flowby's server is not running, so the kits cannot be read" };
  const views = (kits ?? []).map(kitView);
  const ready = views.reduce((n, v) => n + v.ready, 0);
  const total = views.reduce((n, v) => n + v.total, 0);
  return {
    label: "preset kits",
    tone: ready > 0 ? "up" : "idle",
    title: total === 0 ? "no kits" : `${ready} of ${total} styles ready to use`,
  };
}
