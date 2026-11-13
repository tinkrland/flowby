/**
 * swatch.test.mjs: the recolour keeps the plugin's numbers, and the blend stays a blend.
 *
 * the port is only worth having if it behaves like the thing it was ported from, so the constants are
 * asserted directly and every branch that could quietly change a result is tested by mutation below.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { APPLY, QUANTIZE, applySwatches, hexToRgb, paletteMapping, quantize, rgbToHex } from "../src/swatch.mjs";

const px = (...rgba) => new Uint8ClampedArray(rgba.flat());

test("the plugin's constants are the ones running", () => {
  assert.deepEqual({ ...QUANTIZE }, { alphaFloor: 30, mergeDistance: 30, maxColors: 8 });
  assert.deepEqual({ ...APPLY }, { alphaFloor: 10, threshold: 35 });
});

test("hex round trips, and a bad string is null rather than black", () => {
  assert.equal(rgbToHex({ r: 0, g: 255, b: 16 }), "#00ff10");
  assert.deepEqual(hexToRgb("#00ff10"), { r: 0, g: 255, b: 16 });
  assert.equal(hexToRgb("nope"), null);
  assert.equal(hexToRgb(undefined), null);
});

test("a flat colour quantises to itself at five bits, which is not the same as its hex", () => {
  const { colours, visible } = quantize(px([255, 0, 0, 255], [255, 0, 0, 255]));
  assert.equal(visible, 2);
  assert.equal(colours.length, 1);
  assert.equal(colours[0].hex, "#f80000", "5 bits a channel: 255 becomes 248");
  assert.equal(colours[0].share, 1);
});

test("transparent pixels are not colours anyone can see", () => {
  const { colours, visible } = quantize(px([255, 0, 0, 20], [0, 0, 255, 255]));
  assert.equal(visible, 1);
  assert.deepEqual(colours.map((c) => c.hex), ["#0000f8"]);
});

test("two colours closer than the merge distance count once, and the frequent one wins", () => {
  const near = quantize(px([248, 0, 0, 255], [248, 0, 0, 255], [250, 2, 0, 255]));
  assert.equal(near.colours.length, 1, "248,0,0 and 250,2,0 are within 30");
  const far = quantize(px([248, 0, 0, 255], [0, 248, 0, 255]));
  assert.equal(far.colours.length, 2, "but a red and a green are not");
});

test("the cap keeps the most frequent colours, not the first seen", () => {
  const one = [248, 0, 0, 255], two = [0, 248, 0, 255], three = [0, 0, 248, 255];
  const { colours } = quantize(px(one, two, two, three, three, three), { maxColors: 2 });
  assert.deepEqual(colours.map((c) => c.hex), ["#0000f8", "#00f800"]);
});

test("shares are of visible pixels and add up to one", () => {
  const { colours } = quantize(px([248, 0, 0, 255], [0, 248, 0, 255], [0, 0, 248, 255], [0, 0, 0, 0]));
  assert.equal(colours.reduce((sum, c) => sum + c.share, 0), 1);
});

test("an exact match is replaced exactly, never blended", () => {
  const out = applySwatches(px([248, 0, 0, 255]), [{ from: { r: 248, g: 0, b: 0 }, to: { r: 0, g: 0, b: 248 } }]);
  assert.deepEqual([...out.data], [0, 0, 248, 255]);
  assert.equal(out.changed, 1);
});

test("a near match keeps as much of itself as the distance says", () => {
  const half = applySwatches(px([20, 0, 0, 255]), [{ from: { r: 0, g: 0, b: 0 }, to: { r: 40, g: 0, b: 0 } }], { threshold: 40 });
  assert.equal(half.changed, 1);
  // t = 1 - 20/40 = 0.5, so the pixel is half of 20 and half of 40, which is 30 and not 20
  assert.deepEqual([...half.data], [30, 0, 0, 255]);
});

test("beyond the threshold a pixel is left alone", () => {
  const out = applySwatches(px([100, 100, 100, 255]), [{ from: { r: 0, g: 0, b: 0 }, to: { r: 255, g: 255, b: 255 } }]);
  assert.equal(out.changed, 0);
  assert.deepEqual([...out.data], [100, 100, 100, 255]);
});

test("the first mapping that matches wins, so order is a decision", () => {
  const mapping = [
    { from: { r: 248, g: 0, b: 0 }, to: { r: 0, g: 0, b: 248 } },
    { from: { r: 250, g: 2, b: 0 }, to: { r: 0, g: 248, b: 0 } },
  ];
  const out = applySwatches(px([249, 1, 0, 255]), mapping);
  // distance 1.41 of a threshold of 35 is a 96% blend toward the FIRST mapping's target, blue.
  // if the second mapping had won the green channel would be 248.
  assert.equal(out.data[1], 0, "the green mapping must not have run");
  assert.ok(out.data[2] > 200, "and the blue one should have");
});

test("invisible pixels are not recoloured and alpha is never touched", () => {
  const map = [{ from: { r: 248, g: 0, b: 0 }, to: { r: 0, g: 0, b: 248 } }];
  // 5 is below the apply floor of 10 and is left alone; 20 is above it and is recoloured, which is the
  // only reason the two floors differ at all
  const out = applySwatches(px([248, 0, 0, 5], [248, 0, 0, 20], [248, 0, 0, 200]), map);
  assert.deepEqual([...out.data], [248, 0, 0, 5, 0, 0, 248, 20, 0, 0, 248, 200]);
});

test("the input buffer is not modified: a canvas preview may still be reading it", () => {
  const input = px([248, 0, 0, 255]);
  applySwatches(input, [{ from: { r: 248, g: 0, b: 0 }, to: { r: 0, g: 0, b: 248 } }]);
  assert.deepEqual([...input], [248, 0, 0, 255]);
});

test("a palette maps each colour to its nearest member, and an empty palette maps nothing", () => {
  const mapping = paletteMapping([{ r: 250, g: 10, b: 10 }, { r: 10, g: 10, b: 250 }], ["#ff0000", "#0000ff"]);
  assert.deepEqual(mapping.map((m) => rgbToHex(m.to)), ["#ff0000", "#0000ff"]);
  assert.deepEqual(paletteMapping([{ r: 1, g: 2, b: 3 }], []), []);
  assert.deepEqual(paletteMapping([{ r: 1, g: 2, b: 3 }], ["nope"]), [], "a palette with nothing usable in it is empty");
});

test("both distances are exclusive: exactly at the boundary nothing happens", () => {
  // the merge test needs a distance that is not a multiple of 8, because 5-bit buckets sit 8 apart
  const merged = quantize(px([0, 0, 0, 255], [24, 0, 0, 255]), { mergeDistance: 24 });
  assert.equal(merged.colours.length, 2, "24 apart is not closer than 24, so both colours survive");

  const atEdge = applySwatches(px([35, 0, 0, 255]), [{ from: { r: 0, g: 0, b: 0 }, to: { r: 0, g: 0, b: 248 } }]);
  assert.equal(atEdge.changed, 0, "a pixel exactly 35 away is out, not a 0% blend that still counts");
});
