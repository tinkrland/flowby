import test from "node:test";
import assert from "node:assert/strict";

import {
  cameraFromTldraw,
  visiblePage,
  pageToScene,
  sceneToPage,
  pageToScreen,
  screenToPage,
  orthoFrustum,
  cssTransform,
  disagreement,
} from "../src/align.mjs";

const close = (a, b, epsilon = 1e-9) => assert.ok(Math.abs(a - b) < epsilon, `${a} != ${b}`);

test("the two layers agree at the corners, at several zooms and offsets", () => {
  const viewport = { w: 1280, h: 800 };
  for (const camera of [
    { x: 0, y: 0, z: 1 },
    { x: -240, y: 120, z: 1 },
    { x: 51.5, y: -7.25, z: 3.5 },
    { x: 0, y: 0, z: 0.125 },
  ]) {
    const errors = disagreement(camera, viewport);
    for (const error of errors) assert.ok(error < 1e-6, `corner drifted by ${error}px`);
  }
});

test("a page point round-trips through screen and back", () => {
  const camera = { x: 17, y: -33, z: 2.25 };
  const point = { x: 410.5, y: 96.75 };
  const back = screenToPage(pageToScreen(point, camera), camera);
  close(back.x, point.x);
  close(back.y, point.y);
});

test("scene space is page space shifted by the corner, so three.js objects sit where the board drew them", () => {
  const camera = { x: 100, y: 50, z: 2 };
  const scene = pageToScene({ x: 140, y: 90 }, camera);
  close(scene.x, 40);
  close(scene.y, 40);
  const back = sceneToPage(scene, camera);
  close(back.x, 140);
  close(back.y, 90);
});

test("the frustum carries the zoom, so a mesh keeps its size against the sketch beside it", () => {
  const viewport = { w: 1280, h: 800 };
  const near = orthoFrustum({ x: 0, y: 0, z: 1 }, viewport);
  const far = orthoFrustum({ x: 0, y: 0, z: 4 }, viewport);
  close(near.right, 1280);
  close(far.right, 320);
  close(near.right / far.right, 4);
});

test("the visible page is what the container shows, not what the camera is translated by", () => {
  const camera = { x: 200, y: -100, z: 2 };
  const page = visiblePage(camera, { w: 1000, h: 600 });
  assert.deepEqual(page, { x: 200, y: -100, w: 500, h: 300 });
  const corner = pageToScreen({ x: page.x, y: page.y }, camera);
  close(corner.x, 0);
  close(corner.y, 0);
});

test("tldraw's camera converts into this convention without a per-version rewrite", () => {
  const tldrawCamera = { x: 40, y: -20, z: 2 }; // screen = page * 2 + (40, -20)
  const camera = cameraFromTldraw(tldrawCamera);
  close(camera.x, -20);
  close(camera.y, 10);
  // the same page point must land on the same screen pixel under both conventions
  const page = { x: 300, y: 150 };
  const ours = pageToScreen(page, camera);
  close(ours.x, page.x * 2 + 40);
  close(ours.y, page.y * 2 - 20);
});

test("a camera scaled to zero is refused rather than dividing by it", () => {
  assert.throws(() => cameraFromTldraw({ x: 0, y: 0, z: 0 }), /must be positive/);
  assert.throws(() => cameraFromTldraw({ x: 0, y: 0, z: -1 }), /must be positive/);
});

test("css for an html overlay is the same transform the canvas is using", () => {
  const camera = { x: 10, y: 20, z: 2 };
  assert.equal(cssTransform(camera, { x: 15, y: 30 }), "translate(10.000px, 20.000px) scale(2.000000)");
});
