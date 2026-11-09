/**
 * nodeui.test.mjs: what a node card shows, checked against python's real output.
 *
 * the expectations come from fuser's docs and clips (property rows with their own sockets, a fold
 * that hides rather than removes, an Execute control only when something runnable is selected, a
 * command bar that shows each node's type signature) and from the live graph and preset menu the
 * python side emits. nothing here is a fixture written to agree with the code.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as ui from "../src/nodeui.mjs";
import { toFlow } from "../src/graph.mjs";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const flowby = (...args) => JSON.parse(execFileSync(path.join(root, "bin", "flowby"), ["--json", ...args], { encoding: "utf8" }));
const graph = flowby("graph");
const presetMenu = flowby("presets");
const presets = Array.isArray(presetMenu) ? presetMenu : Object.values(presetMenu).find(Array.isArray);
const nodes = graph.pipeline.nodes;
const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
const node = (op) => nodes.find((n) => n.op === op);

// --- sockets --------------------------------------------------------------------------------

test("a port that takes one connection is a circle and one that takes many is an oval", () => {
  assert.equal(ui.socketShape({ dtype: "image", many: false }), "circle");
  assert.equal(ui.socketShape({ dtype: "image", many: true }), "oval");
  assert.equal(ui.socketShape({ dtype: "image" }), "circle", "an unstated port is single");
});

test("an oval is taller than a circle but exactly as wide, so rows stay aligned", () => {
  assert.equal(ui.SOCKET.oval.w, ui.SOCKET.circle.w);
  assert.ok(ui.SOCKET.oval.h > ui.SOCKET.circle.h);
});

test("every port on the live board gets a shape that matches what python says about it", () => {
  let checked = 0;
  for (const n of nodes) for (const p of [...Object.values(n.inputs), ...Object.values(n.outputs)]) {
    assert.equal(ui.socketShape(p), p.many ? "oval" : "circle");
    checked++;
  }
  assert.ok(checked > 10);
});

// --- the card -------------------------------------------------------------------------------

test("a card lists inputs, then properties, then outputs, in that order", () => {
  const card = ui.cardOf(node("control.depth"));
  assert.deepEqual(card.inputs.map((r) => r.name), ["image"]);
  assert.deepEqual(card.properties.map((r) => r.name), ["weight", "blur"]);
  assert.deepEqual(card.outputs.map((r) => r.name), ["out"]);
});

test("every row carries its wire colour, so the socket on it is already the right hue", () => {
  const card = ui.cardOf(node("control.depth"));
  assert.equal(card.inputs[0].hex, "#22c55e");
  assert.equal(card.outputs[0].role, "depth");
});

test("a property row shows the value, not just the name", () => {
  const card = ui.cardOf(node("control.depth"));
  assert.deepEqual(card.properties.map((r) => [r.name, r.value]), [["weight", "0.85"], ["blur", "2"]]);
});

test("placement bookkeeping is not a property: an asset digest is never shown as a row", () => {
  const el = nodes.find((n) => n.op.startsWith("element.") && n.params.asset);
  assert.ok(el, "the demo board has an element with an asset");
  assert.equal(ui.cardOf(el).properties.some((r) => r.name === "asset"), false);
  assert.equal(ui.isTunable("anything", "sha256:" + "a".repeat(64)), false);
  assert.equal(ui.isTunable("label", "x"), false);
  assert.equal(ui.isTunable("weight", 0.5), true);
});

test("a long list of properties folds behind a count, and nothing is removed", () => {
  const many = { id: "n", op: "x.y", label: "x", inputs: {}, outputs: {}, params: { a: 1, b: 2, c: 3, d: 4, e: 5, f: 6 } };
  const folded = ui.cardOf(many);
  assert.equal(folded.properties.length, 3);
  assert.equal(folded.hidden, 3);
  assert.equal(folded.foldLabel, "3 properties hidden");
  const open = ui.cardOf(many, { expanded: true });
  assert.equal(open.properties.length, 6);
  assert.equal(open.hidden, 0);
  assert.equal(open.foldLabel, null);
});

test("one hidden property reads in the singular", () => {
  const n = { id: "n", op: "x.y", label: "x", inputs: {}, outputs: {}, params: { a: 1, b: 2, c: 3, d: 4 } };
  assert.equal(ui.cardOf(n).foldLabel, "1 property hidden");
});

test("a card with few properties has no fold at all", () => {
  assert.equal(ui.cardOf(node("control.depth")).foldLabel, null);
});

test("values read at a glance: numbers trimmed, booleans in words, long text cut, objects counted", () => {
  assert.equal(ui.formatValue(0.123456789), "0.123");
  assert.equal(ui.formatValue(4), "4");
  assert.equal(ui.formatValue(true), "on");
  assert.equal(ui.formatValue(false), "off");
  assert.equal(ui.formatValue(null), "none");
  assert.equal(ui.formatValue(""), "empty");
  assert.equal(ui.formatValue("a".repeat(40)).length, 22);
  assert.ok(ui.formatValue("a".repeat(40)).endsWith("…"));
  assert.equal(ui.formatValue(["otf", "ttf"]), "2 items");
  assert.equal(ui.formatValue(["x"]), "1 item");
  assert.equal(ui.formatValue({ a: 1, b: 2 }), "2 fields");
});

test("an element is marked as one, so the skin can show its picture as the body", () => {
  assert.equal(ui.cardOf(nodes.find((n) => n.op.startsWith("element."))).isElement, true);
  assert.equal(ui.cardOf(node("control.depth")).isElement, false);
});

test("card height grows with its rows, the fold line and a preview, and the three agree with the constants", () => {
  const plain = ui.cardOf(node("control.depth"));
  const h = ui.cardHeight(plain);
  assert.equal(h, ui.CARD.head + 4 * ui.CARD.row + ui.CARD.pad);   // 1 in + 2 props + 1 out
  assert.equal(ui.cardHeight(plain, { preview: true }), h + ui.CARD.preview);
  const folded = ui.cardOf({ id: "n", op: "x.y", label: "x", inputs: {}, outputs: {}, params: { a: 1, b: 2, c: 3, d: 4 } });
  assert.equal(ui.cardHeight(folded), ui.CARD.head + 3 * ui.CARD.row + ui.CARD.fold + ui.CARD.pad);
});

// --- running --------------------------------------------------------------------------------

test("an element is placed and a step is run, so only steps are runnable", () => {
  assert.equal(ui.runnable(node("control.depth")), true);
  assert.equal(ui.runnable(nodes.find((n) => n.op.startsWith("element."))), false);
});

test("the Execute control is hidden until a runnable node is selected", () => {
  assert.equal(ui.executeState([], byId).visible, false);
  const el = nodes.find((n) => n.op.startsWith("element.")).id;
  assert.equal(ui.executeState([el], byId).visible, false, "an element alone gives nothing to run");
  const step = node("control.depth");
  const one = ui.executeState([step.id], byId);
  assert.deepEqual([one.visible, one.count, one.label], [true, 1, `run ${step.label}`]);
});

test("selecting several steps says how many it will run, and ignores the elements among them", () => {
  const steps = nodes.filter((n) => !n.op.startsWith("element.")).slice(0, 3).map((n) => n.id);
  const el = nodes.find((n) => n.op.startsWith("element.")).id;
  const s = ui.executeState([...steps, el], byId);
  assert.equal(s.count, 3);
  assert.equal(s.label, "run 3 steps");
});

test("a selection that names a node which is gone does not crash and does not count", () => {
  assert.equal(ui.executeState(["ghost"], byId).visible, false);
});

test("the action bar differs by what the node is: a step can run, an element can be replaced", () => {
  const stepActions = ui.actionsFor(node("control.depth")).map((a) => a.id);
  const elActions = ui.actionsFor(nodes.find((n) => n.op.startsWith("element."))).map((a) => a.id);
  assert.ok(stepActions.includes("run") && !elActions.includes("run"));
  assert.ok(elActions.includes("replace") && !stepActions.includes("replace"));
  assert.equal(ui.actionsFor(node("control.depth")).filter((a) => a.primary).length, 1, "exactly one primary action");
});

// --- the command bar ------------------------------------------------------------------------

const rows = ui.commandRows(presets);

test("every real preset becomes a row with a type signature in the wire colours", () => {
  assert.equal(rows.length, presets.length);
  const mesh = rows.find((r) => r.id === "sketch-to-mesh");
  assert.deepEqual(mesh.signature.chips.map((c) => [c.label, c.hex]), [["IMG", "#22c55e"], ["3D", "#ef4444"]]);
});

test("text, image, video and mesh each have a distinct chip label", () => {
  const labels = ["text", "image", "video", "mesh"].map((d) => ui.commandRows([{ name: "x", label: "x", from: d, to: d, stage: "explore" }])[0].signature.chips[0].label);
  assert.deepEqual(labels, ["TXT", "IMG", "VID", "3D"]);
});

test("an empty query lists everything, explore before refine before output", () => {
  const all = ui.searchCommands(rows, "");
  assert.equal(all.length, rows.length);
  const order = { explore: 0, refine: 1, output: 2 };
  const stages = all.map((r) => order[r.stage]);
  assert.deepEqual(stages, [...stages].sort((a, b) => a - b), "stage order holds when scores tie");
});

test("every word in the query must match, so adding a word narrows the list", () => {
  const one = ui.searchCommands(rows, "mesh").length;
  const two = ui.searchCommands(rows, "mesh sketch").length;
  assert.ok(two <= one);
  assert.ok(two >= 1);
  assert.equal(ui.searchCommands(rows, "zzzznothing").length, 0);
});

test("a match on the name outranks a match only in the blurb", () => {
  const r = ui.searchCommands(rows, "mesh");
  const firstBlurbOnly = r.findIndex((x) => !x.label.toLowerCase().includes("mesh") && !x.id.includes("mesh") && x.signature.from !== "mesh" && x.signature.to !== "mesh");
  const lastNamed = r.map((x) => x.label.toLowerCase().includes("mesh") || x.id.includes("mesh")).lastIndexOf(true);
  if (firstBlurbOnly !== -1) assert.ok(lastNamed < firstBlurbOnly, "named matches come first");
});

test("search ignores case and extra spaces", () => {
  assert.deepEqual(ui.searchCommands(rows, "  MESH ").map((r) => r.id), ui.searchCommands(rows, "mesh").map((r) => r.id));
});

test("the bar can be narrowed to what the selected element is", () => {
  const forModel = ui.searchCommands(rows, "", { appliesTo: "model" });
  assert.ok(forModel.length > 0 && forModel.length < rows.length);
  assert.ok(forModel.every((r) => r.appliesTo.includes("model")));
});

test("a preset that names a model is searchable by it", () => {
  const withModel = rows.find((r) => r.models.length);
  assert.ok(withModel);
  assert.ok(ui.searchCommands(rows, withModel.models[0]).some((r) => r.id === withModel.id));
});

// --- quick connect --------------------------------------------------------------------------

test("dragging from an image output offers only presets that take an image", () => {
  const q = ui.quickConnect(rows, { side: "out", dtype: "image" });
  assert.ok(q.options.length > 0);
  assert.ok(q.options.every((r) => r.signature.from === "image"));
});

test("dragging from an input offers only presets that give that type", () => {
  const q = ui.quickConnect(rows, { side: "in", dtype: "mesh" });
  assert.ok(q.options.every((r) => r.signature.to === "mesh"));
});

test("nothing incompatible is ever offered, and an empty answer says why", () => {
  for (const dtype of ["text", "image", "video", "mesh"]) for (const side of ["in", "out"]) {
    const q = ui.quickConnect(rows, { side, dtype });
    const key = side === "out" ? "from" : "to";
    assert.ok(q.options.every((r) => r.signature[key] === dtype), `${side} ${dtype}`);
  }
  const none = ui.quickConnect([], { side: "out", dtype: "video" });
  assert.equal(none.empty, "nothing takes video here");
});

// --- no palette of its own ------------------------------------------------------------------

test("this file names no colour of its own: the wire hues come from wires.mjs", async () => {
  const fs = await import("node:fs");
  const src = fs.readFileSync(new URL("../src/nodeui.mjs", import.meta.url), "utf8").split("\n").filter((l) => !l.trim().startsWith("*") && !l.trim().startsWith("//")).join("\n");
  assert.equal(/#[0-9a-fA-F]{6}\b/.test(src), false);
});

test("a node with no op still gets a card, so layout never crashes on a half-built node", () => {
  const card = ui.cardOf({ id: "n", inputs: { a: { dtype: "image" } }, outputs: {} });
  assert.equal(card.isElement, false);
  assert.equal(card.inputs.length, 1);
  assert.equal(ui.runnable({ id: "n" }), true);
});

// --- idle and connected sockets: fuser draws an unwired port dim and a wired one bright ---------

test("a port is connected exactly when a wire in the real graph touches it", () => {
  const { pipeline } = graph;
  const wired = ui.connectedPorts(pipeline);
  let touched = 0;
  for (const w of pipeline.wires) {
    assert.ok(wired.get(w.from.node).has(`out:${w.from.port}`), `${w.from.node}.${w.from.port} should be connected`);
    assert.ok(wired.get(w.to.node).has(`in:${w.to.port}`), `${w.to.node}.${w.to.port} should be connected`);
    touched += 2;
  }
  assert.ok(touched > 0, "the real graph has wires to check");
  // and nothing else: count every port on every node and compare
  const total = [...wired.values()].reduce((n, set) => n + set.size, 0);
  const distinct = new Set(pipeline.wires.flatMap((w) => [`${w.from.node}|out:${w.from.port}`, `${w.to.node}|in:${w.to.port}`])).size;
  assert.equal(total, distinct);
});

test("a port nothing is wired to is idle, and the real graph has some", () => {
  const { pipeline } = graph;
  const wired = ui.connectedPorts(pipeline);
  let idle = 0;
  for (const node of pipeline.nodes) {
    const card = ui.cardOf(node, { connected: wired.get(node.id) ?? new Set() });
    for (const r of [...card.inputs, ...card.outputs]) if (!r.connected) idle += 1;
  }
  assert.ok(idle > 0, "a board with every port wired would make this test meaningless");
});

test("a card marks its own rows connected from the set it is given, and idle without one", () => {
  const node = { id: "n", op: "x.y", label: "n", inputs: { a: { dtype: "image" } }, outputs: { out: { dtype: "image" } } };
  const wired = ui.cardOf(node, { connected: new Set(["in:a"]) });
  assert.equal(wired.inputs[0].connected, true);
  assert.equal(wired.outputs[0].connected, false);
  assert.equal(ui.cardOf(node).inputs[0].connected, false, "no set means nothing is wired");
});

test("a connected socket is fully opaque and an idle one is dim but still visible enough to drag from", () => {
  assert.equal(ui.socketOpacity({ connected: true }), 1);
  const idle = ui.socketOpacity({ connected: false });
  assert.ok(idle < 1, "idle must read differently from connected");
  assert.ok(idle >= 0.3, "idle must stay findable, since a port you cannot see is a port you cannot drag from");
});

test("an input and an output with the same name on one node are tracked separately", () => {
  const wired = ui.connectedPorts({ wires: [{ from: { node: "a", port: "out" }, to: { node: "b", port: "out" } }] });
  assert.deepEqual([...wired.get("a")], ["out:out"]);
  assert.deepEqual([...wired.get("b")], ["in:out"]);
});

test("toFlow hands every card the ports that are wired to it, as plain arrays", async () => {
  const { toFlow } = await import("../src/graph.mjs");
  const { pipeline } = graph;
  const flow = toFlow(pipeline);
  const w = pipeline.wires[0];
  const src = flow.nodes.find((n) => n.id === w.from.node);
  assert.ok(Array.isArray(src.data.connected));
  assert.ok(src.data.connected.includes(`out:${w.from.port}`));
  JSON.stringify(flow.nodes.map((n) => n.data));   // survives serialisation: no Set in props
});

// --- zooming to a node: fuser's double-click ---------------------------------------------------

test("framing a node centres it in the pane", () => {
  const box = { x: 400, y: 120, width: 232, height: 140 };
  const pane = { width: 1200, height: 700 };
  const cam = ui.frameNode(box, pane);
  const screenX = box.x * cam.zoom + cam.x + (box.width * cam.zoom) / 2;
  const screenY = box.y * cam.zoom + cam.y + (box.height * cam.zoom) / 2;
  assert.ok(Math.abs(screenX - 600) < 0.001 && Math.abs(screenY - 350) < 0.001, `centre lands at ${screenX},${screenY}`);
});

test("a card takes about half the pane when framed, and the zoom is clamped both ways", () => {
  // a box wide enough that the 1.4 cap does not bite: 900 wide wants 600/900 = 0.667x, so it fills half the width
  const cam = ui.frameNode({ x: 0, y: 0, width: 900, height: 300 }, { width: 1200, height: 700 }, { fill: 0.5 });
  assert.ok(Math.abs(900 * cam.zoom - 600) < 1, `fills half the pane width, got ${900 * cam.zoom}`);
  // and an ordinary 232px card in this pane is capped, not stretched to fill it
  assert.equal(ui.frameNode({ x: 0, y: 0, width: 232, height: 140 }, { width: 1200, height: 700 }).zoom, 1.4);
  assert.equal(ui.frameNode({ x: 0, y: 0, width: 10, height: 10 }, { width: 1200, height: 700 }).zoom, 1.4, "a tiny card is not blown up past the maximum");
  assert.equal(ui.frameNode({ x: 0, y: 0, width: 90000, height: 90000 }, { width: 1200, height: 700 }).zoom, 0.15, "a huge one is not shrunk below the minimum");
});

test("framing refuses a box or pane with no size instead of returning NaN", () => {
  for (const [box, pane] of [[{ x: 0, y: 0, width: 0, height: 10 }, { width: 100, height: 100 }], [{ x: 0, y: 0, width: 10, height: 10 }, { width: 0, height: 100 }], [undefined, { width: 1, height: 1 }]]) {
    assert.throws(() => ui.frameNode(box, pane), /needs a box and a pane with a size/);
  }
});

test("framing the real board's nodes gives a finite camera for every one", () => {
  const flow = toFlow(graph.pipeline);
  for (const n of flow.nodes) {
    const cam = ui.frameNode({ x: n.position.x, y: n.position.y, width: n.width, height: n.height }, { width: 1200, height: 700 });
    assert.ok([cam.x, cam.y, cam.zoom].every(Number.isFinite), n.id);
  }
});
