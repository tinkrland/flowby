/**
 * board.test.mjs: which board the page draws, and what it says about it.
 *
 * the failure worth a test is the silent one: a page that shows the committed snapshot while a person
 * believes they are editing the live board. so the tests are about the *claim* as much as the choice.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { LIVE, SNAPSHOT, afterPlacing, choose, drawable } from "../src/board.mjs";

const snapshot = {
  title: "the demo board",
  legend: { text: "amber", image: "green" },
  roles: { style: "green" },
  pipeline: { scene: "board", nodes: [{ id: "sketch-1" }], wires: [{ from: "a", to: "b" }] },
};
const live = { title: "my board", pipeline: { scene: "board", nodes: [{ id: "text-1" }], wires: [] } };

test("a live board that answered is the one drawn", () => {
  const picked = choose({ live, snapshot });
  assert.equal(picked.kind, LIVE);
  assert.equal(picked.doc.title, "my board");
  assert.equal(picked.doc.pipeline.nodes[0].id, "text-1");
});

test("the live board borrows the legend and roles it does not publish", () => {
  const picked = choose({ live, snapshot });
  assert.deepEqual(picked.doc.legend, snapshot.legend);
  assert.deepEqual(picked.doc.roles, snapshot.roles);
  // and its own board is not overwritten by the snapshot's
  assert.deepEqual(picked.doc.pipeline.nodes, live.pipeline.nodes);
});

test("a live board with its own legend keeps it", () => {
  const own = { ...live, legend: { text: "amber" }, roles: { mine: "x" } };
  const picked = choose({ live: own, snapshot });
  assert.deepEqual(picked.doc.legend, { text: "amber" });
  assert.deepEqual(picked.doc.roles, { mine: "x" });
});

test("with no server the snapshot is drawn, and the page says it cannot be edited", () => {
  const picked = choose({ snapshot });
  assert.equal(picked.kind, SNAPSHOT);
  assert.match(picked.note, /nothing can be placed/);
});

test("a server that answers with something undrawable falls back rather than drawing a hole", () => {
  // a 200 with an error body, or a half-written board: either way the canvas must not be handed it
  for (const bad of [null, {}, { pipeline: {} }, { pipeline: { nodes: [] } }, { pipeline: { nodes: [], wires: null } }]) {
    const picked = choose({ live: bad, snapshot });
    assert.equal(picked.kind, SNAPSHOT, JSON.stringify(bad));
  }
});

test("nothing at all is a sentence, not an empty canvas with no explanation", () => {
  const picked = choose({});
  assert.equal(picked.kind, null);
  assert.equal(picked.doc, null);
  assert.match(picked.note, /npm run graph/);
});

test("drawable is strict about the two arrays the canvas reads", () => {
  assert.equal(drawable(snapshot), true);
  assert.equal(drawable({ pipeline: { nodes: [], wires: [] } }), true);
  assert.equal(drawable({ pipeline: { nodes: [] } }), false);
  assert.equal(drawable(undefined), false);
});

test("a place action repeats python's sentence, because python wrote it", () => {
  assert.equal(afterPlacing({ receipt: { said: "crayon on the board, with 2 nodes behind it" } }, LIVE),
    "crayon on the board, with 2 nodes behind it");
});

test("a place that came back without a sentence says so instead of inventing one", () => {
  assert.match(afterPlacing({}, LIVE), /gave no sentence/);
});

test("placing while the page shows the snapshot says the board did not move", () => {
  assert.match(afterPlacing({}, SNAPSHOT), /snapshot/);
});
