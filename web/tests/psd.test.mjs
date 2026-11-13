/** real bytes: write a layered psd with ag-psd, read it back, and plan the board from it. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { writePsdBuffer, readPsd, initializeCanvas } from "ag-psd";

// node has no canvas. ag-psd only needs image data to decode a layer's channel bytes, so the stub
// gives it the two shapes it asks for and nothing else.
initializeCanvas(
  (w, h) => ({ width: w, height: h, getContext: () => ({}) }),
  (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
);
import { psdLayers, boardPlan, psdKind, effectsOf, FIDELITY } from "../src/psd.mjs";
import * as intake from "../src/intake.mjs";

test("a psd written and read back yields its layers in order, and the plan places what it can", () => {
  const bytes = writePsdBuffer({
    width: 40, height: 30,
    children: [
      { name: "plate", left: 0, top: 0, right: 40, bottom: 30, opacity: 255, blendMode: "normal",
        imageData: { data: new Uint8Array(40 * 30 * 4).fill(200), width: 40, height: 30 } },
      { name: "type", left: 4, top: 6, right: 24, bottom: 16, text: { text: "flowby" } },
      { name: "hidden one", left: 1, top: 1, right: 8, bottom: 8, hidden: true },
    ],
  });
  // useImageData keeps this test out of a canvas: node has none, and the browser path takes the canvas
  const psd = readPsd(new Uint8Array(bytes), { useImageData: true, skipCompositeImageData: true, skipThumbnail: true });
  const tree = psdLayers(psd);
  assert.deepEqual(tree.layers.map((l) => l.name), ["plate", "type", "hidden one"]);
  // the third layer carries no pixel data in this fixture, so it is honestly a shape, not an image
  assert.deepEqual(tree.layers.map((l) => l.kind), ["image", "text", "shape"]);
  assert.equal(tree.width, 40);
  assert.equal(tree.layers[1].text, "flowby", "the words survive the round trip");
  assert.equal(tree.layers[0].raw.name, "plate", "the raw layer is kept for its pixels");

  const plan = boardPlan(tree);
  assert.deepEqual(plan.place.map((p) => p.name), ["plate", "type"], "hidden layers are not placed");
  // the image layer's extent is real; the text layer's is not in the file, so it is null and the host
  // measures the words instead of trusting a zero
  assert.deepEqual([plan.place[0].x, plan.place[0].y, plan.place[0].w, plan.place[0].h], [0, 0, 40, 30]);
  assert.deepEqual([plan.place[1].x, plan.place[1].y, plan.place[1].w, plan.place[1].h], [4, 6, null, null]);
  assert.match(plan.summary, /2 of 3 layers placed: 1 hidden/);
});

test("a psd is recognised by its bytes, not its extension", () => {
  const real = new Uint8Array([0x38, 0x42, 0x50, 0x53, 0, 1]);
  assert.equal(intake.sniff(real), "psd");
  const plan = intake.classify({ name: "looks-like.png", bytes: real });
  assert.equal(plan.via, "layers");
});

test("a layer kind is decided by what it holds", () => {
  assert.equal(psdKind({ text: { text: "x" } }), "text");
  assert.equal(psdKind({ children: [{}] }), "group");
  assert.equal(psdKind({ canvas: {} }), "image");
  assert.equal(psdKind({}), "shape");
});

test("effects are named, and an empty one is not an effect", () => {
  assert.deepEqual(effectsOf({ effects: { dropShadow: {}, stroke: [], bevel: [{}, {}] } }), ["dropShadow", "bevel"]);
  assert.deepEqual(effectsOf({}), []);
});

test("a layer with no place on the canvas is counted, not placed at 0,0", () => {
  const tree = psdLayers({ children: [{ name: "nowhere", canvas: {}, left: 0, top: 0 }] });
  const plan = boardPlan(tree);
  assert.equal(plan.place.length, 0, "placing it at zero would put it somewhere nobody chose");
  assert.equal(plan.skipped.boxless, 1);
});

test("the fidelity line says what an import cannot do", () => {
  assert.match(FIDELITY.psd, /nothing here writes a psd back/);
});
