/**
 * rail.test.mjs: the rail keeps its order and tells the truth about what it can do, and the popover
 * groups real presets without inventing a group or dropping one.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { readFileSync } from "node:fs";

import * as rail from "../src/rail.mjs";

const p = (name, over = {}) => ({ name, label: name, blurb: "", from: "text", to: "image", stage: "explore", estimate: 1, ...over });

test("five slots, in the reference order", () => {
  assert.deepEqual(rail.RAIL.map((s) => s.id), ["add", "library", "command", "nodes", "settings"]);
  assert.equal(rail.RAIL[3].key, "shift+a");
});

test("run starts off and says why; a slot whose panel is still in the header says that too", () => {
  const s = rail.railState({});
  assert.equal(s.run.on, false);
  assert.match(s.run.why, /select a node first/);
  assert.equal(s.visible, true);
  const byId = Object.fromEntries(s.items.map((i) => [i.id, i]));
  assert.deepEqual(Object.entries(byId).filter(([, i]) => i.on).map(([id]) => id), ["add", "command", "nodes"]);
  assert.match(byId.library.why, /still in the header/);
  assert.match(byId.settings.why, /still in the header/);
});

test("a selection makes run live, and clears the reason", () => {
  const s = rail.railState({ hasSelection: true });
  assert.equal(s.run.on, true);
  assert.equal(s.run.why, null);
});

test("a phone gets no rail, and every slot says why rather than vanishing", () => {
  const s = rail.railState({ hasSelection: true, narrow: true });
  assert.equal(s.visible, false);
  assert.equal(s.items.length, 5, "the slots keep their place");
  assert.equal(s.items.every((i) => i.on === false && /desktop/.test(i.why)), true, "on a phone every slot is off for the same reason");
  assert.equal(s.run.on, false);
});

test("every preset lands in exactly one group, and the total is the list length", () => {
  const presets = [p("a"), p("b", { to: "mesh" }), p("c", { to: "text", from: "image" })];
  const g = rail.nodeGroups(presets);
  assert.equal(g.total, 3);
  assert.equal(g.groups.reduce((n, x) => n + x.count, 0), 3);
  assert.deepEqual(g.groups.map((x) => x.dtype), ["text", "image", "mesh"], "wire order, and empty types dropped");
});

test("a type nothing writes does not appear", () => {
  const g = rail.nodeGroups([p("a"), p("b")]);
  assert.deepEqual(g.groups.map((x) => x.dtype), ["image"]);
  assert.equal(g.groups.find((x) => x.dtype === "video"), undefined);
});

test("an undeclared output type goes to other, never nowhere", () => {
  const g = rail.nodeGroups([p("a"), p("b", { to: "pointcloud" }), p("c", { to: null })]);
  const other = g.groups.find((x) => x.dtype === "other");
  assert.ok(other, "other exists when something does not fit");
  assert.deepEqual(other.rows.map((r) => r.name), ["b", "c"]);
  assert.equal(g.total, 3);
});

test("rows are ordered by stage, then by label", () => {
  const g = rail.nodeGroups([
    p("z", { stage: "output" }),
    p("b", { stage: "explore" }),
    p("a", { stage: "explore" }),
    p("m", { stage: "refine" }),
  ]);
  assert.deepEqual(g.groups[0].rows.map((r) => r.name), ["a", "b", "m", "z"]);
});

test("a missing estimate is null, not zero", () => {
  const g = rail.nodeGroups([p("a", { estimate: undefined }), p("b", { estimate: "1.8" })]);
  assert.deepEqual(g.groups[0].rows.map((r) => r.estimate), [null, null]);
});

test("an estimate is words, and a missing one is unknown rather than free", () => {
  assert.equal(rail.estimateText(0), "free");
  assert.equal(rail.estimateText(1), "1 min");
  assert.equal(rail.estimateText(1.84), "1.8 min");
  assert.equal(rail.estimateText(null), "cost unknown");
  assert.equal(rail.estimateText(undefined), "cost unknown");
  assert.equal(rail.estimateText(Number.NaN), "cost unknown");
  assert.equal(rail.estimateText("2"), "cost unknown", "a string is not a measurement");
});

test("a card that makes several results says how many, in vectary's shape", () => {
  assert.equal(rail.countedName({ label: "one frame" }), "one frame", "one variant is the label, not '1 image'");
  assert.equal(rail.countedName({ label: "four takes", variants: 4, to: "image" }), "4 images");
  assert.equal(rail.countedName({ label: "clips", variants: 3, to: "video" }), "3 clips");
  // a declared noun wins, because "6 meshes" would be wrong for six materials
  assert.equal(rail.countedName({ label: "apply materials", variants: 6, to: "mesh", variantNoun: "materials" }), "6 materials");
  assert.equal(rail.countedName({ label: "x", variants: 2, to: "pointcloud" }), "2 results", "an unknown wire is not guessed at");
});

test("every row in the real menu has a name a person can read", () => {
  const presets = JSON.parse(readFileSync(new URL("../public/presets.json", import.meta.url), "utf8")).presets;
  const g = rail.nodeGroups(presets);
  for (const group of g.groups) for (const row of group.rows) {
    assert.equal(typeof row.show, "string");
    assert.ok(row.show.length > 0, `${row.name} has no readable name`);
    if (row.variants > 1) assert.match(row.show, /^\d+ /, `${row.name} hides its count`);
  }
});
