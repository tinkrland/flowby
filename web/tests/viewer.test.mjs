/**
 * viewer.test.mjs: a phone gets the graph as text, and never a confident number it does not have.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import * as v from "../src/viewer.mjs";

const node = (id, over = {}) => ({ id, op: `op.${id}`, label: id, cost: { minutes: 0, gpu: false }, ...over });

test("the line between editor and viewer is 760px, exclusive", () => {
  assert.equal(v.isNarrow(390), true);
  assert.equal(v.isNarrow(759), true);
  assert.equal(v.isNarrow(760), false);
  assert.equal(v.isNarrow(1500), false);
});

test("a width that is not a number is not a reason to hide the board", () => {
  assert.equal(v.isNarrow(NaN), false);
  assert.equal(v.isNarrow(undefined), false);
  assert.equal(v.isNarrow("390"), false);
});

test("one row per node, in graph order, nothing dropped and nothing invented", () => {
  const rows = v.viewerRows([node("a"), node("b"), node("c")]);
  assert.deepEqual(rows.map((r) => r.id), ["a", "b", "c"]);
  assert.equal(rows.length, 3);
});

test("a node with no cost block reads cost unknown, never free", () => {
  const [row] = v.viewerRows([{ id: "a", op: "op.a", label: "a" }]);
  assert.equal(row.known, false);
  assert.equal(row.text, "cost unknown");
  assert.equal(row.pips, 0);
});

test("a cost block with no number in it is still unknown, not free", () => {
  const rows = v.viewerRows([
    node("empty", { cost: {} }),
    node("null", { cost: { minutes: null, gpu: true } }),
    node("words", { cost: { minutes: "3", gpu: false } }),
  ]);
  assert.deepEqual(rows.map((r) => r.known), [false, false, false]);
  assert.deepEqual(rows.map((r) => r.text), ["cost unknown", "cost unknown", "cost unknown"]);
  assert.equal(rows[1].gpu, false, "a gpu flag with no minutes is not a cost either");
});

test("zero minutes is free, and a fraction rounds up for the bars but not for the words", () => {
  const rows = v.viewerRows([node("z", { cost: { minutes: 0, gpu: false } }), node("f", { cost: { minutes: 0.4, gpu: true } })]);
  assert.equal(rows[0].text, "free");
  assert.equal(rows[0].pips, 0);
  assert.equal(rows[1].text, "0.4 min");
  assert.equal(rows[1].pips, 1, "a 0.4 minute node still draws one bar, because it is not free");
  assert.equal(rows[1].gpu, true);
});

test("the total is a floor, and says so, when any node's cost is unknown", () => {
  const rows = v.viewerRows([node("a", { cost: { minutes: 1.2, gpu: false } }), { id: "b", op: "op.b", label: "b" }]);
  const total = v.viewerTotal(rows);
  assert.equal(total.minutes, 1.2);
  assert.equal(total.unknown, 1);
  assert.match(total.spoken, /at least/);
  assert.match(total.spoken, /1 not counted/);
});

test("a fully known total is stated plainly with the node count", () => {
  const total = v.viewerTotal(v.viewerRows([node("a", { cost: { minutes: 1.1, gpu: false } }), node("b", { cost: { minutes: 0.4, gpu: false } })]));
  assert.equal(total.unknown, 0);
  assert.equal(total.spoken, "1.5 min across 2 nodes");
});

test("the note tells the person why the board is not here", () => {
  assert.match(v.VIEWER.note, /desktop or tablet/);
  assert.equal(v.EDITOR_MIN_WIDTH, 760);
});
