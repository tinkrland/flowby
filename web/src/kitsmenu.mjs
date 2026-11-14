/**
 * kitsmenu.mjs: what the preset kits menu shows, decided without a DOM.
 *
 * python owns each member's true state (kits.py: listed, corpus, training, ready) and whether it
 * can run. this file only arranges that for reading, and its one rule mirrors the plug's: a member
 * is offered as usable only when python said `runnable`. a listed style is a name on a list, and
 * the menu says so in its own word instead of looking like a button.
 *
 * there is a third state between a name and a trained style, and it is the one the handdrawn kit is in:
 * a member can have WORDS (looks.py) without having weights. that member cannot run, because a run needs
 * a model, but it can be placed: the direction becomes a text node and the preset behind it. so `usable`
 * stays false and `placeable` becomes true, and the two words are different words.
 */

export const STATE_WORD = Object.freeze({
  listed: "listed, not built yet",
  corpus: "gathering images",
  training: "training",
  ready: "ready",
});

/**
 * the word for a member's state. an unknown state reads as listed: the weakest claim, never a stronger
 * one. a member with words but no weights says exactly that, because "listed, not built yet" would be a
 * lie about a member that can already be placed.
 */
export function wordFor(state, { worded = false } = {}) {
  if (worded && !(state in STATE_WORD)) return "worded, not trained";
  if (worded && state === "listed") return "worded, not trained";
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
  const worded = members.filter((m) => m.worded === true && Boolean(m.look)).length;
  return {
    id: kit.id,
    label: kit.label,
    blurb: kit.blurb,
    ready,
    worded,
    total: members.length,
    summary: `${ready} of ${members.length} ready${worded ? `, ${worded} worded` : ""}`,
    rows: members.map((m) => ({
      id: m.id,
      label: m.label,
      blurb: m.blurb,
      depth: m.depth,
      state: m.state,
      word: wordFor(m.state, { worded: m.worded === true }),
      // usable only when python says so AND the state agrees; anything else is a name on a list
      usable: m.runnable === true && m.state === "ready",
      // placeable means the direction can become nodes now. it is not runnable: no model runs yet
      look: m.look ?? null,
      worded: m.worded === true && Boolean(m.look),
      placeable: m.worded === true && Boolean(m.look),
    })),
  };
}

/** the header button: it says how many members can really run, never how many exist */
export function kitsButton(kits, { reachable = true } = {}) {
  if (!reachable) return { label: "preset kits", tone: "off", title: "flowby's server is not running, so the kits cannot be read" };
  const views = (kits ?? []).map(kitView);
  const ready = views.reduce((n, v) => n + v.ready, 0);
  const worded = views.reduce((n, v) => n + v.worded, 0);
  const total = views.reduce((n, v) => n + v.total, 0);
  if (total === 0) return { label: "preset kits", tone: "idle", title: "no kits" };
  if (ready > 0) return { label: "preset kits", tone: "up", title: `${ready} of ${total} styles ready to use` };
  return {
    label: "preset kits",
    // not green: nothing can run. not off either: there is work here worth pressing
    tone: "idle",
    title: worded > 0 ? `nothing trained yet; ${worded} of ${total} have wording and can be placed` : `0 of ${total} styles ready to use`,
  };
}
