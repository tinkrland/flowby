/**
 * recipe.test.mjs: the recipe card's claims, in words.
 *
 * the card is drawn from python's payload, so these tests are about the three ways a card can mislead:
 * a required mark on something that has a saved example, a fixed setting offered as though it were a
 * control, and a run that is disabled without saying why.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { cardView, shelfView } from "../src/recipe.mjs";

const base = {
  name: "heron sketch",
  brief: "transform a sketch into a painted still",
  version: "3e2e52",
  author: "liat",
  output: "image",
  category: "image",
  inputs: [
    { label: "fidelity", means: "obey the drawing, or drift", required: false,
      example: { kind: "value", value: 6 }, target: { preset: "sketch-to-render", param: "fidelity" } },
  ],
  slots: [],
  advanced: [{ preset: "sketch-to-render", name: "seed", value: 41, means: "another roll of the dice" }],
  hidden: [{ preset: "sketch-to-render", name: "keep", value: 0.5, means: "runs at 0.5; the card has no control for it" }],
  needs: { runtime: "the machine you are on", gpu: false, cost: "free", weights: ["sdxl-turbo"], files: [], paid: true },
  run: { label: "run", enabled: true, blocked_by: [] },
};

test("a control with a saved example gets no required mark, and shows the example", () => {
  const v = cardView(base);
  assert.equal(v.inputs[0].mark, "");
  assert.equal(v.inputs[0].required, false);
  assert.equal(v.inputs[0].example, "6");
  assert.equal(v.inputs[0].where, "sketch-to-render.fidelity");
});

test("a required thing is marked, and an empty slot is the case where that happens", () => {
  const v = cardView({ ...base, slots: [{ preset: "style-transfer", slot: "look", filled: false, required: true }] });
  assert.equal(v.slots[0].mark, "*");
  assert.equal(v.slots[0].means, "nothing in it");
  assert.equal(v.wanted, 1);
});

test("a filled slot says wired and is not marked", () => {
  const v = cardView({ ...base, slots: [{ preset: "style-transfer", slot: "look", filled: true, required: false }] });
  assert.equal(v.slots[0].mark, "");
  assert.equal(v.slots[0].means, "wired");
  assert.equal(v.wanted, 0);
});

test("a fixed setting is drawn as fixed, never as a control", () => {
  const v = cardView(base);
  const fixed = v.fixed[0];
  assert.equal(fixed.label, "keep");
  assert.equal(fixed.value, "0.5");
  assert.equal(fixed.where, "sketch-to-render");
  // nothing in a fixed row claims to be adjustable: no value to type, no range, no control name
  assert.deepEqual(Object.keys(fixed).sort(), ["label", "means", "value", "where"]);
});

test("the advanced fold holds the seed and says what it is for", () => {
  const v = cardView(base);
  assert.deepEqual(v.advanced.map((r) => [r.label, r.value]), [["seed", "41"]]);
  assert.ok(v.advanced[0].means.length > 5);
});

test("a disabled run names its blocker instead of just going quiet", () => {
  const v = cardView({ ...base, run: { label: "run", enabled: false, blocked_by: ["the look slot on style-transfer"] } });
  assert.equal(v.run.enabled, false);
  assert.equal(v.run.why, "blocked by the look slot on style-transfer");
});

test("a run disabled with no named blocker still explains itself", () => {
  const v = cardView({ ...base, run: { enabled: false, blocked_by: [] } });
  assert.equal(v.run.why, "this card cannot run");
});

test("an enabled run says nothing in the why slot", () => {
  assert.equal(cardView(base).run.why, "");
});

test("cost is stated, and free-to-run with paid weights does not collapse into free", () => {
  const free = cardView(base);
  const cost = free.needs.find((r) => r.key === "cost");
  assert.equal(cost.says, "free to run here, paid weights");
  const reallyFree = cardView({ ...base, needs: { ...base.needs, weights: [], paid: false } });
  assert.equal(reallyFree.needs.find((r) => r.key === "cost").says, "free");
  const priced = cardView({ ...base, needs: { ...base.needs, cost: "36 minutes of a 4090" } });
  assert.equal(priced.needs.find((r) => r.key === "cost").says, "costs (36 minutes of a 4090)");
});

test("a card with no version says unsigned rather than vundefined", () => {
  assert.equal(cardView({ ...base, version: "" }).stamp, "unsigned");
  assert.equal(cardView(base).stamp, "v3e2e52 · liat");
  assert.equal(cardView({ ...base, author: "" }).stamp, "v3e2e52");
});

test("a payload that is not a card draws nothing rather than an empty shell", () => {
  for (const bad of [null, undefined, {}, { brief: "no name" }, "a string"]) assert.equal(cardView(bad), null);
});

test("the shelf lists what is on the board and says how it stands", () => {
  const v = shelfView([{ ...base, element: "sketch-1" }, { ...base, element: "text-2", name: "caption", version: "", run: { enabled: false } }]);
  assert.equal(v.rows.length, 2);
  assert.deepEqual(v.rows.map((r) => r.version), ["v3e2e52", "unsigned"]);
  assert.deepEqual(v.rows.map((r) => r.ready), [true, false]);
  assert.equal(v.empty, "");
});

test("an empty shelf says how a chain gets there, and an unreachable server says that instead", () => {
  assert.match(shelfView([]).empty, /apply a preset/);
  const off = shelfView([], { reachable: false });
  assert.match(off.empty, /server is not running/);
  assert.equal(off.rows.length, 0);
});
