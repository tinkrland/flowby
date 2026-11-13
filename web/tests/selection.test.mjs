/**
 * selection.test.mjs: the pill tells the truth about a selection, especially about its price.
 *
 * the three things that could go wrong quietly, and are each tested: a number that is invented when
 * nobody declared one, a selection that includes a node the board does not have, and a cost that
 * hides the gpu share it will have to spend.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import * as s from "../src/selection.mjs";

const node = (id, over = {}) => ({ id, op: `op.${id}`, label: id, params: {}, cost: { minutes: 0, gpu: false }, ...over });

test("nothing selected means no pill at all", () => {
  assert.equal(s.pill([], [node("a")]).visible, false);
  assert.equal(s.pill(undefined, [node("a")]).visible, false);
});

test("a stale id is dropped, not counted", () => {
  const p = s.pill(["a", "gone"], [node("a")]);
  assert.equal(p.count, 1);
  assert.deepEqual(p.chosen.map((n) => n.id), ["a"]);
});

test("a selection of only stale ids is no selection, so no pill", () => {
  const p = s.pill(["gone", "also-gone"], [node("a")]);
  assert.equal(p.visible, false);
  assert.equal(p.count, 0);
});

test("the selection keeps graph order even when the ids arrive shuffled", () => {
  const p = s.pill(["c", "a", "b"], [node("a"), node("b"), node("c")]);
  assert.deepEqual(p.chosen.map((n) => n.id), ["a", "b", "c"]);
});

test("cost is the sum of the nodes' declared minutes, and only theirs", () => {
  const c = s.costOf([node("a", { cost: { minutes: 0.4, gpu: false } }), node("b", { cost: { minutes: 3.2, gpu: true } }), node("c", { cost: { minutes: 0.9, gpu: false } })]);
  assert.equal(c.minutes, 4.5);
  assert.equal(c.gpu, 3.2);
  assert.equal(c.known, 3);
});

test("a node that declares no cost adds nothing and is not counted as known", () => {
  const c = s.costOf([node("a", { cost: undefined }), node("b", { cost: { minutes: 2, gpu: false } })]);
  assert.equal(c.minutes, 2);
  assert.equal(c.known, 1);
});

test("no declared costs reads cost unknown, never a confident zero", () => {
  const l = s.costLabel(s.costOf([node("a", { cost: undefined })]));
  assert.equal(l.text, "cost unknown");
  assert.equal(l.timed, false);
});

test("declared zeros read free, which is a different fact from unknown", () => {
  const l = s.costLabel(s.costOf([node("a")]));
  assert.equal(l.text, "free");
  assert.equal(l.timed, false);
});

test("a gpu step is named as gpu time, in minutes of its own", () => {
  const l = s.costLabel(s.costOf([node("a", { cost: { minutes: 0.6, gpu: false } }), node("b", { cost: { minutes: 3.2, gpu: true } })]));
  assert.equal(l.text, "3.8 min");
  assert.equal(l.gpu, true);
  assert.match(l.hint, /3\.2 min on a gpu/);
});

test("a selection that is all gpu says so once, not per node", () => {
  const l = s.costLabel(s.costOf([node("a", { cost: { minutes: 2, gpu: true } }), node("b", { cost: { minutes: 2, gpu: true } })]));
  assert.equal(l.text, "4 min");
  assert.match(l.hint, /gpu throughout/);
});

test("cpu-only time says cpu, so a plugged gpu is not implied", () => {
  const l = s.costLabel(s.costOf([node("a", { cost: { minutes: 1.5, gpu: false } })]));
  assert.equal(l.text, "1.5 min");
  assert.equal(l.gpu, false);
  assert.match(l.hint, /cpu only/);
});

test("one node is titled by its label, several are titled by their count", () => {
  assert.equal(s.pill(["a"], [node("a", { label: "the owl" })]).title, "the owl");
  assert.equal(s.pill(["a", "b"], [node("a"), node("b")]).title, "2 nodes");
});

test("a node with no label falls back to its op, not to an empty title", () => {
  assert.equal(s.pill(["a"], [node("a", { label: "" })]).title, "op.a");
});

test("lock becomes unlock only when every selected node is locked", () => {
  const nodes = [node("a"), node("b")];
  const one = s.pill(["a", "b"], nodes, { locked: ["a"] });
  assert.equal(one.actions.find((a) => a.name === "lock").label, "lock");
  const both = s.pill(["a", "b"], nodes, { locked: ["a", "b"] });
  assert.equal(both.actions.find((a) => a.name === "lock").label, "unlock");
});

test("every action is offered only when there is something to act on", () => {
  const empty = s.pill([], [node("a")]);
  assert.equal(empty.actions.every((a) => a.enabled === false), true);
  assert.equal(empty.actions.every((a) => typeof a.reason === "string"), true);
  const some = s.pill(["a"], [node("a")]);
  assert.equal(some.actions.every((a) => a.enabled && a.reason === null), true);
});

test("fields are the tunable params, named, with the control each value wants", () => {
  const n = node("a", { params: { text: "a dog", steps: 24, fast: true, asset: "sha256:deadbeef", meta: { a: 1 } } });
  const f = s.fieldsOf(n, (name) => name !== "asset");
  assert.deepEqual(f.map((x) => [x.name, x.kind]), [["text", "text"], ["steps", "number"], ["fast", "switch"], ["meta", "readonly"]]);
});

test("fields keep the node's own key order so a field does not jump between openings", () => {
  const f = s.fieldsOf(node("a", { params: { zeta: 1, alpha: 2 } }));
  assert.deepEqual(f.map((x) => x.name), ["zeta", "alpha"]);
});

test("the preset row is listed and off, with the reason it cannot work yet", () => {
  const rows = s.moreMenu();
  const preset = rows.find((r) => r.name === "preset");
  assert.equal(preset.enabled, false);
  assert.match(preset.reason, /store/);
});

test("the pill carries no fields for a multi-node selection, because one form cannot be several", () => {
  const p = s.pill(["a", "b"], [node("a", { params: { text: "x" } }), node("b", { params: { text: "y" } })], { tunable: () => true });
  assert.deepEqual(p.fields, []);
});
