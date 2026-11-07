/**
 * gesture.test.mjs: dropping and pasting onto the canvas.
 *
 * the expectations come from what fuser's clips and docs show, not from the code under test:
 * a drop on bare canvas makes nodes, a drop over a node tints it first and replaces it on release,
 * and a paste is a file import only when the user is not typing. the last one matters most here,
 * because this panel has a password field and a link field, and a canvas that took ctrl+v from
 * them would make the figma door unusable.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as g from "../src/gesture.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const file = (n) => new Uint8Array(fs.readFileSync(path.join(here, "fixtures", "files", n)));

const nodes = {
  photo: { label: "owl photo", accepts: true },
  gen: { label: "Flux Dev", accepts: false },
};

// --- what a drag looks like -----------------------------------------------------------------

test("only a drag that carries files lights up the canvas", () => {
  assert.equal(g.carriesFiles(["Files"]), true);
  assert.equal(g.carriesFiles(["text/plain", "Files"]), true);
  assert.equal(g.carriesFiles(["text/plain", "text/uri-list"]), false);
  assert.equal(g.carriesFiles(undefined), false);
  assert.equal(g.dragState({ types: ["text/plain"] }).active, false);
});

test("over bare canvas the drag says it will add new nodes", () => {
  const s = g.dragState({ types: ["Files"], nodes });
  assert.deepEqual([s.active, s.target, s.verb], [true, null, "add as new nodes"]);
});

test("over a node that takes files the drag names the node it will replace, before release", () => {
  const s = g.dragState({ types: ["Files"], over: "photo", nodes });
  assert.deepEqual([s.target, s.verb], ["photo", "replace owl photo"]);
});

test("over a node that does not take files the drag says so and offers no verb", () => {
  const s = g.dragState({ types: ["Files"], over: "gen", nodes });
  assert.equal(s.verb, null);
  assert.match(s.refuses, /Flux Dev does not take files/);
});

test("an id that is not a known node is treated as bare canvas", () => {
  assert.equal(g.dragState({ types: ["Files"], over: "ghost", nodes }).target, null);
  assert.equal(g.dropTarget({ over: "ghost", nodes }).action, "create");
});

// --- where a drop lands ---------------------------------------------------------------------

test("a drop on bare canvas creates one node per file", () => {
  assert.deepEqual(g.dropTarget({ nodes, count: 3 }), { action: "create", count: 3 });
});

test("a drop on a node that takes files replaces its content", () => {
  assert.deepEqual(g.dropTarget({ over: "photo", nodes, count: 1 }), { action: "replace", node: "photo" });
});

test("several files on one node replace it with the first and add the rest, and say so", () => {
  const r = g.dropTarget({ over: "photo", nodes, count: 3 });
  assert.deepEqual([r.action, r.node, r.extra], ["replace-first", "photo", 2]);
  assert.match(r.note, /takes one file, so the first replaces it and 2 more are added as new nodes/);
});

test("a drop on a node that takes no files is refused and creates nothing behind the user's back", () => {
  const r = g.dropTarget({ over: "gen", nodes, count: 2 });
  assert.equal(r.action, "refuse");
  assert.match(r.reason, /drop on the empty canvas to add a new node/);
});

// --- paste ----------------------------------------------------------------------------------

test("typing in a text field, a textarea or a link field is never hijacked", () => {
  for (const t of [{ tagName: "TEXTAREA" }, { tagName: "INPUT", type: "text" }, { tagName: "INPUT", type: "password" },
    { tagName: "INPUT" }, { tagName: "INPUT", type: "url" }, { tagName: "DIV", isContentEditable: true }]) {
    assert.equal(g.typing(t), true, JSON.stringify(t));
    assert.deepEqual(g.readPaste({ files: [{ name: "x.png" }], hasText: false, target: t }).take, []);
  }
});

test("a checkbox, a button or a range is not a typing target, so a paste there still imports", () => {
  for (const t of [{ tagName: "INPUT", type: "checkbox" }, { tagName: "BUTTON" }, { tagName: "INPUT", type: "range" }, { tagName: "DIV" }, null]) {
    assert.equal(g.typing(t), false, JSON.stringify(t));
  }
  assert.equal(g.readPaste({ files: [{ name: "x.png" }], target: { tagName: "INPUT", type: "checkbox" } }).take.length, 1);
});

test("a paste with files on the bare canvas is an import", () => {
  const r = g.readPaste({ files: [{ name: "a.png" }, { name: "b.png" }], target: { tagName: "BODY" } });
  assert.equal(r.take.length, 2);
  assert.equal(r.silent, false);
});

test("a paste of plain text on the canvas is ignored without comment", () => {
  const r = g.readPaste({ files: [], hasText: true, target: { tagName: "BODY" } });
  assert.deepEqual([r.take.length, r.why, r.silent], [0, "text", true]);
});

test("an empty paste is ignored without comment", () => {
  assert.deepEqual(g.readPaste({}).why, "empty");
});

test("a pasted screenshot gets a name made of its time and type, and two in one second do not collide", () => {
  const at = new Date("2026-11-08T03:45:09Z");
  const a = g.nameForPaste({ name: "image.png", type: "image/png" }, 0, at);
  const b = g.nameForPaste({ name: "image.png", type: "image/png" }, 1, at);
  assert.equal(a, "pasted-2026-11-08-03-45-09-1.png");
  assert.notEqual(a, b);
  assert.equal(g.nameForPaste({ name: "", type: "image/jpeg" }, 0, at), "pasted-2026-11-08-03-45-09-1.jpg");
});

test("a pasted file that already has a real name keeps it", () => {
  assert.equal(g.nameForPaste({ name: "owl.webp", type: "image/webp" }, 0), "owl.webp");
});

// --- the layout fuser's clip shows ----------------------------------------------------------

test("new nodes sit in a row, as wide as their picture asks, and never overlap", () => {
  const row = g.layoutRow([{ width: 800, height: 1200 }, { width: 1000, height: 1000 }, { width: 1600, height: 900 }], { origin: { x: 100, y: 50 } });
  assert.equal(row[0].box.x, 100);
  assert.ok(row[0].box.w < row[1].box.w, "a portrait is narrower than a square at the same height");
  assert.ok(row[1].box.w < row[2].box.w, "a square is narrower than a landscape");
  for (let i = 1; i < row.length; i++) {
    assert.ok(row[i].box.x >= row[i - 1].box.x + row[i - 1].box.w + 28, `node ${i} overlaps the one before it`);
  }
  assert.ok(row.every((r) => r.box.y === 50 && r.box.h === 220), "one row, one height");
});

test("an item with no known size is laid out square, and nothing is wider than the cap", () => {
  const row = g.layoutRow([{}, { width: 9000, height: 100 }]);
  assert.equal(row[0].box.w, 220);
  assert.equal(row[1].box.w, 360);
});

test("a very thin picture still gets a node wide enough to grab", () => {
  assert.equal(g.layoutRow([{ width: 10, height: 1000 }])[0].box.w, 96);
});

// --- what is taken --------------------------------------------------------------------------

test("every dropped file is either to place or refused with a reason, and none vanishes", () => {
  const files = [["a.png", "a.png"], ["clip.mp4", "a.mp4"], ["t.png", "text.png"], ["d.pdf", "a.pdf"], ["p.zip", "a.zip"]]
    .map(([name, f]) => ({ name, bytes: file(f) }));
  const { placed, refused } = g.takeFiles(files);
  assert.equal(placed.length + refused.length, files.length);
  assert.deepEqual(refused.map((r) => r.name), ["t.png", "d.pdf"]);
  assert.equal(placed.find((p) => p.name === "p.zip").needs, "unpack");
  assert.equal(placed.find((p) => p.name === "a.png").needs, null);
});

test("a refusal here is the same sentence the panel would give", () => {
  const { refused } = g.takeFiles([{ name: "d.pdf", bytes: file("a.pdf") }]);
  assert.match(refused[0].reason, /^pdf pages are not read here/);
});
