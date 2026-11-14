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

test("a member with words but no weights says so, and is placeable rather than usable", () => {
  const v = k.kitView(kit([
    m("pencil-sketch", { state: "listed", look: "look.pencil-sketch", worded: true }),
    m("cyanotype", { state: "listed" }),
  ]));
  const [sketch, cyan] = v.rows;
  assert.equal(sketch.word, "worded, not trained");
  assert.equal(sketch.placeable, true);
  assert.equal(sketch.usable, false);          // placing is not running: no model runs yet
  assert.equal(sketch.look, "look.pencil-sketch");
  assert.equal(cyan.placeable, false);
  assert.equal(cyan.word, k.STATE_WORD.listed);
});

test("a worded flag with no look behind it is not placeable", () => {
  // the two fields come from python; believing one without the other would put a button on nothing
  const v = k.kitView(kit([m("a", { worded: true }), m("b", { look: "look.b" })]));
  assert.deepEqual(v.rows.map((r) => r.placeable), [false, false]);
  assert.equal(v.worded, 0);
});

test("the summary counts worded members beside ready ones, and says nothing when there are none", () => {
  const mixed = k.kitView(kit([m("a", { worded: true, look: "look.a" }), m("b")]));
  assert.equal(mixed.summary, "0 of 2 ready, 1 worded");
  assert.equal(k.kitView(kit([m("b")])).summary, "0 of 1 ready");
});

test("a training member keeps its training word even when it has wording", () => {
  // "worded" must not hide that a corpus is being gathered; the stronger fact wins
  const v = k.kitView(kit([m("a", { state: "corpus", look: "look.a", worded: true })]));
  assert.equal(v.rows[0].word, k.STATE_WORD.corpus);
});

test("the header button offers placing when nothing is trained but something is worded", () => {
  const b = k.kitsButton([kit([m("a", { worded: true, look: "look.a" }), m("b")])]);
  assert.match(b.title, /1 of 2 have wording and can be placed/);
  assert.notEqual(b.tone, "up");               // green is for a run, and nothing here can run
});

test("an unknown state with wording still reads as worded rather than as a made-up state", () => {
  assert.equal(k.wordFor("invented", { worded: true }), "worded, not trained");
  assert.equal(k.wordFor("invented"), k.STATE_WORD.listed);
});
