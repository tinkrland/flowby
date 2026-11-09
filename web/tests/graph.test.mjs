/**
 * graph.test.mjs: the seam, tested from node with no DOM.
 *
 * the failures worth catching here are the ones a screenshot does not show: a wire into a port
 * that does not exist, a colour that drifted from python's palette, a layout that reorders itself
 * between renders, or two nodes landing on top of each other the way they did when python owned
 * the grid.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { check, nodeHeight, NODE_W, toFlow } from "../src/graph.mjs";
import { CARD } from "../src/nodeui.mjs";
import { portStyle, WIRES, wireFor } from "../src/wires.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../..");

/** the real board, as `flowby graph` prints it. python is the source of truth, not a fixture. */
function graphJson() {
  const out = execFileSync(path.join(repo, "bin", "flowby"), ["--json", "graph"], {
    encoding: "utf8",
  });
  return JSON.parse(out);
}

const tiny = {
  nodes: [
    { id: "a", op: "element.sketch", label: "the owl", instance: null, params: {}, rank: 0, row: 0,
      inputs: {}, outputs: { out: { dtype: "image", role: null } } },
    { id: "b", op: "mesh.triposr", label: "build the mesh", instance: "a/x", params: {}, rank: 1, row: 0,
      inputs: { image: { dtype: "image", role: null, many: false } },
      outputs: { out: { dtype: "mesh", role: null } } },
  ],
  wires: [{ from: { node: "a", port: "out" }, to: { node: "b", port: "image" }, dtype: "image" }],
};

test("the palette in the browser is the palette in python", () => {
  const legend = graphJson().legend;
  assert.deepEqual(
    legend.map((w) => ({ dtype: w.dtype, colour: w.colour, hex: w.hex })),
    WIRES.map((w) => ({ dtype: w.dtype, colour: w.colour, hex: w.hex })),
    "wires.mjs drifted from dtypes.py, which is the file that decides what a wire means",
  );
  for (const wire of legend) {
    assert.equal(wireFor(wire.dtype).hex, wire.hex);
  }
});

test("a fifth wire colour is a refusal, not a grey line", () => {
  assert.throws(() => wireFor("audio"), /no colour for the "audio" wire/);
});

test("a role is drawn differently from a plain wire of the same colour", () => {
  const plain = portStyle({ dtype: "image" });
  const depth = portStyle({ dtype: "image", role: "depth" });
  assert.equal(plain.stroke, depth.stroke, "same colour: it is the same kind of thing");
  assert.equal(plain.dashed, false);
  assert.equal(depth.dashed, true, "a control channel has to be visibly not a picture");
});

test("the real board compiles into nodes and edges without a single dangling wire", () => {
  const { pipeline } = graphJson();
  const flow = toFlow(pipeline);
  assert.equal(flow.nodes.length, pipeline.nodes.length);
  assert.equal(flow.edges.length, pipeline.wires.length);
  for (const edge of flow.edges) {
    assert.ok(pipeline.nodes.some((n) => n.id === edge.source));
    assert.ok(pipeline.nodes.some((n) => n.id === edge.target));
    assert.match(edge.sourceHandle, /^out:/);
    assert.match(edge.targetHandle, /^in:/);
    assert.equal(edge.type, "wire");
  }
});

test("python no longer ships geometry, so the renderer is the only layout", () => {
  const { pipeline } = graphJson();
  for (const node of pipeline.nodes) {
    assert.equal(node.pos, undefined, "a position here would be a second layout system");
    assert.equal(typeof node.rank, "number");
    assert.equal(typeof node.row, "number");
  }
});

test("the layout runs left to right along the depth python reports", () => {
  const { pipeline } = graphJson();
  const flow = toFlow(pipeline);
  const byId = new Map(flow.nodes.map((n) => [n.id, n]));
  for (const edge of flow.edges) {
    const from = byId.get(edge.source);
    const to = byId.get(edge.target);
    if (to.data.rank === from.data.rank) continue; // a shared head feeding two tails
    assert.ok(from.position.x < to.position.x, `${edge.id} runs backwards`);
  }
  // every node sits inside the extent dagre reported, or the minimap is lying
  for (const node of flow.nodes) {
    assert.ok(node.position.x >= 0 && node.position.y >= 0, `${node.id} is outside the canvas`);
    assert.ok(node.position.x + node.width <= flow.extent.width);
  }
});

test("no two nodes overlap, which is what dagre is here to guarantee", () => {
  const flow = toFlow(graphJson().pipeline);
  for (let i = 0; i < flow.nodes.length; i += 1) {
    for (let j = i + 1; j < flow.nodes.length; j += 1) {
      const a = flow.nodes[i];
      const b = flow.nodes[j];
      const apart =
        a.position.x + a.width <= b.position.x ||
        b.position.x + b.width <= a.position.x ||
        a.position.y + a.height <= b.position.y ||
        b.position.y + b.height <= a.position.y;
      assert.ok(apart, `${a.id} and ${b.id} are on top of each other`);
    }
  }
});

test("laying the same graph out twice gives the same pixels", () => {
  const { pipeline } = graphJson();
  assert.deepEqual(toFlow(pipeline), toFlow(pipeline));
});

test("a node is as tall as its ports need, and never shorter than its head", () => {
  const one = { inputs: { a: { dtype: "image" } }, outputs: {} };
  const five = { inputs: {}, outputs: Object.fromEntries("abcde".split("").map((k) => [k, { dtype: "image" }])) };
  assert.ok(nodeHeight(one) > 0);
  assert.ok(nodeHeight(five) > nodeHeight(one));
  assert.equal(NODE_W, CARD.width, "layout and the drawn card share one width");
});

test("a wire into a port that does not exist refuses by name", () => {
  const broken = structuredClone(tiny);
  broken.wires[0].to.port = "geometry";
  assert.throws(() => check(broken), /b\.geometry, which is not one of its inputs/);
});

test("a wire that lies about its dtype refuses", () => {
  const broken = structuredClone(tiny);
  broken.wires[0].dtype = "mesh";
  assert.throws(() => check(broken), /labelled mesh but leaves a image port/);
});

test("two wires of the same shape are one wire, so the second is refused", () => {
  const doubled = structuredClone(tiny);
  doubled.wires.push(structuredClone(tiny.wires[0]));
  assert.throws(() => check(doubled), /two wires share the shape/);
});

test("a one-row chain of cards fits a laptop viewport at a zoom where property rows stay legible", () => {
  const { pipeline } = graphJson();
  const flow = toFlow(pipeline);
  const xs = flow.nodes.map((n) => n.position.x), x2 = flow.nodes.map((n) => n.position.x + n.width);
  const width = Math.max(...x2) - Math.min(...xs);
  const fit = 1200 / width;
  // 0.63 was the zoom at the old 104px column gap, and at that size 11px row text is about 7px.
  assert.ok(fit >= 0.7, `the live board fits at ${fit.toFixed(2)}x, which is too small to read`);
});

test("columns are far enough apart for a wire to curve, so tightening the layout cannot flatten them", () => {
  const { pipeline } = graphJson();
  const flow = toFlow(pipeline);
  const by = Object.fromEntries(flow.nodes.map((n) => [n.id, n]));
  for (const e of flow.edges) {
    const gap = by[e.target].position.x - (by[e.source].position.x + by[e.source].width);
    assert.ok(gap >= 40, `${e.id} spans only ${gap}px, which is not enough to draw a curve`);
  }
});
