/**
 * kitsmenu.test.mjs: the kits menu says only what python reported, and never offers a listed style as usable.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import * as k from "../src/kitsmenu.mjs";

const m = (id, over = {}) => ({ id, label: id, blurb: "b", kind: "style", parent: null, preset: null, state: "listed", runnable: false, ...over });
const kit = (members, over = {}) => ({ id: "k", label: "k", blurb: "kb", members, ...over });

test("a listed style is not usable and says it is not built yet", () => {
  const v = k.kitView(kit([m("cyanotype")]));
  assert.equal(v.rows[0].usable, false);
  assert.equal(v.rows[0].word, "listed, not built yet");
  assert.equal(v.summary, "0 of 1 ready");
});

test("only a member python called runnable AND ready is usable", () => {
  const v = k.kitView(kit([m("a", { state: "ready", runnable: true }), m("b", { state: "ready", runnable: false }), m("c", { state: "training", runnable: true })]));
  assert.deepEqual(v.rows.map((r) => r.usable), [true, false, false]);
  assert.equal(v.summary, "1 of 3 ready");
});

test("the count is made from the members, not trusted from a header that could disagree", () => {
  const v = k.kitView(kit([m("a"), m("b")], { ready: 2, total: 99 }));
  assert.equal(v.ready, 0);
  assert.equal(v.total, 2);
});

test("an unknown state reads as listed, the weakest claim", () => {
  assert.equal(k.wordFor("bogus"), k.STATE_WORD.listed);
  assert.equal(k.wordFor(undefined), k.STATE_WORD.listed);
});

test("every state python can report has its own words", () => {
  for (const s of ["listed", "corpus", "training", "ready"]) assert.ok(k.STATE_WORD[s].length > 3, s);
  assert.equal(new Set(Object.values(k.STATE_WORD)).size, 4);
});

test("subtypes sit directly under their parent, indented, whatever order they arrive in", () => {
  const rows = k.kitView(kit([m("cross", { parent: "textile" }), m("analog-x"), m("textile"), m("woven", { parent: "textile" })])).rows;
  assert.deepEqual(rows.map((r) => [r.id, r.depth]), [["analog-x", 0], ["textile", 0], ["cross", 1], ["woven", 1]]);
});

test("a subtype whose parent is missing is shown, not dropped", () => {
  const rows = k.kitView(kit([m("orphan", { parent: "gone" })])).rows;
  assert.equal(rows.length, 1);
  assert.equal(rows[0].depth, 0);
});

test("no members and no kits are empty, not an error", () => {
  assert.equal(k.kitView(kit([])).summary, "0 of 0 ready");
  assert.equal(k.kitsButton(null).title, "no kits");
  assert.deepEqual(k.ordered(undefined), []);
});

test("the header button never says styles are ready when none can run", () => {
  const b = k.kitsButton([kit([m("a"), m("b")])]);
  assert.equal(b.tone, "idle");
  assert.equal(b.title, "0 of 2 styles ready to use");
});

test("the header button counts across kits and goes green only for a really ready member", () => {
  const b = k.kitsButton([kit([m("a", { state: "ready", runnable: true })]), kit([m("b"), m("c")])]);
  assert.equal(b.tone, "up");
  assert.equal(b.title, "1 of 3 styles ready to use");
});

test("an unreachable server is its own state, not an empty kit list", () => {
  const b = k.kitsButton([], { reachable: false });
  assert.equal(b.tone, "off");
  assert.match(b.title, /not running/);
});
