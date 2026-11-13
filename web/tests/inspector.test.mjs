/**
 * the panel's two jobs: say what a node did, and say what running it again would do. the tests are
 * mostly about the second one's honesty, because a panel that rounds "never run" into "0 runs, 0 min"
 * is a panel that has stopped being a history.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { age, history, panel, summary } from "../src/inspector.mjs";

const doc = (over = {}) => ({
  work: { run: ["a", "b"], reuse: ["c"], minutes: 4.2 },
  nodes: {
    a: {
      id: "a", op: "image.diffuse", label: "relight", params: { strength: 0.5, steps: 20 },
      minutes: 3.2, gpu: true, verdict: "run", because: "no run for this signature",
      runs: [],
    },
    b: {
      id: "b", op: "mesh.frost", label: "frost", params: {}, minutes: 1, gpu: false,
      verdict: "reuse", runs: [{ id: "b#2", state: "failed", minutes: 0.2, at: 1000, note: "oom" }],
    },
    c: {
      id: "c", op: "image.pass", label: "pass", params: { amount: 0.3333333 }, minutes: 0,
      gpu: false, verdict: "reuse",
      runs: [
        { id: "c#1", state: "ok", minutes: 0.4, at: 1000 },
        { id: "c#2", state: "failed", minutes: 0.1, at: 2000 },
        { id: "c#3", state: "ok", minutes: 1.25, at: 3000, artifacts: ["one", "two"] },
      ],
    },
  },
  ...over,
});

test("a node that has never run says so instead of showing a confident zero", () => {
  const p = panel("a", doc(), 5000);
  assert.equal(p.empty, true);
  assert.equal(p.count, 0);
  assert.match(p.emptyLine, /never run/);
  assert.equal(p.rows.length, 0);
});

test("the header says what a run would cost, not what the last one spent", () => {
  const p = panel("c", doc(), 5000);
  assert.equal(p.cost.value, "0");
  assert.equal(p.cost.gpu, false);
  assert.equal(p.rows[0].spent, "1.3");  // the newest run spent 1.25
});

test("the history is newest first and keeps its failures", () => {
  const p = panel("c", doc(), 5000);
  assert.deepEqual(p.rows.map((r) => r.id), ["c#3", "c#2", "c#1"]);
  assert.deepEqual(p.rows.map((r) => r.state), ["ok", "failed", "ok"]);
  assert.equal(p.cancelled, 1);
  assert.equal(p.rows[0].artifacts, 2);
});

test("the verdict is python's, and it is repeated with python's own reason", () => {
  assert.match(panel("a", doc(), 5000).verdictLine, /no run for this signature/);
  assert.equal(panel("a", doc(), 5000).verdict, "run");
  const reused = panel("c", doc(), 5000);
  assert.equal(reused.verdict, "reuse");
  assert.match(reused.verdictLine, /reuse the run from/);
});

test("a node with runs can still be stale, and the verdict says so", () => {
  // the case that matters: it has run before, its inputs changed, so those runs cannot be stood on
  const stale = doc();
  stale.nodes.d = {
    id: "d", op: "image.pass", label: "pass", params: {}, minutes: 0.5, gpu: false,
    verdict: "run", because: "upstream will run again",
    runs: [{ id: "d#1", state: "ok", minutes: 0.5, at: 3000 }],
  };
  const p = panel("d", stale, 5000);
  assert.equal(p.count, 1);
  assert.equal(p.verdict, "run");
  assert.match(p.verdictLine, /upstream will run again/);
});

test("an unknown node has no panel rather than an empty one", () => {
  assert.equal(panel("nope", doc()), null);
  assert.equal(panel("a", null), null);
});

test("params are shown at three decimals, never as a float's full length", () => {
  const p = panel("c", doc(), 5000);
  assert.deepEqual(p.params, [{ name: "amount", value: "0.333" }]);
});

test("ages are coarse, and a run with no time is not 'just now'", () => {
  assert.equal(age(0), "unknown");
  assert.equal(age(NaN), "unknown");
  // a real clock is always positive, so the fixtures use one big enough that a two-day-old run still
  // lands after the epoch; below that the code calls the timestamp unknown, which is correct
  const now = 1_000_000;
  assert.equal(age(now - 1, now), "just now");
  assert.equal(age(now - 120, now), "2m ago");
  assert.equal(age(now - 7200, now), "2h ago");
  assert.equal(age(now - 180_000, now), "2d ago");
  assert.equal(age(now, now), "just now");
});

test("the board says how much of the work is actually work", () => {
  assert.equal(summary(doc()).line, "2 to run (4.2 min), 1 reused");
  assert.equal(summary({ work: { run: [], reuse: ["a", "b"] } }).line, "nothing to run: all 2 nodes reuse a run");
  assert.equal(summary({ work: { run: [], reuse: [] } }).line, "nothing on this board to run");
});

test("a failed run is never counted as a success anywhere in the panel", () => {
  const p = panel("b", doc(), 5000);
  assert.equal(p.rows.length, 1);
  assert.equal(p.rows[0].state, "failed");
  assert.equal(p.empty, false);
});

test("a history row with a non-string note does not leak an object into the panel", () => {
  const weird = doc();
  weird.nodes.a.runs = [{ id: "a#1", state: "ok", minutes: 1, at: 1000, note: { why: "no" } }];
  assert.equal(history(weird.nodes.a, 5000)[0].note, "");
});
