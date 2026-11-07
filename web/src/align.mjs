/**
 * align.mjs: the one piece of arithmetic that decides whether the two layers are one board.
 *
 * tldraw draws the spatial layer into a DOM canvas it owns. react-three-fiber draws the 3d
 * elements into a second canvas that sits exactly on top of it. those two canvases only agree if
 * the webgl camera is derived from tldraw's camera on every frame, and if the derivation is a pure
 * function, because a camera that drifts by a pixel per pan looks like a bug in the 3d engine.
 *
 * so: the board's camera is `{x, y, z}`, where a page point becomes a screen point by
 *
 *     screen = (page - camera.xy) * camera.z
 *
 * which means the camera's x and y are the page coordinates of the container's top-left corner, and
 * z is the scale. that is the convention this repo uses everywhere. tldraw reports its own camera
 * with a screen-space translation instead, so `cameraFromTldraw` converts rather than this file
 * being rewritten per version.
 */

/**
 * tldraw reports `screen = page * z + t`. convert that into the page-space corner this repo uses.
 * @param {{x: number, y: number, z: number}} tldrawCamera
 * @returns {{x: number, y: number, z: number}}
 */
export function cameraFromTldraw(tldrawCamera) {
  const { x, y, z } = tldrawCamera;
  if (!(z > 0)) throw new Error(`camera scale must be positive, got ${z}`);
  return { x: -x / z, y: -y / z, z };
}

/**
 * the page-space rectangle the container is showing.
 * @param {{x: number, y: number, z: number}} camera
 * @param {{w: number, h: number}} viewport css pixels
 */
export function visiblePage(camera, viewport) {
  return {
    x: camera.x,
    y: camera.y,
    w: viewport.w / camera.z,
    h: viewport.h / camera.z,
  };
}

/**
 * page coordinates into scene coordinates, which is what the three.js objects are positioned in:
 * relative to the viewport's top-left corner, y still pointing down the page.
 */
export function pageToScene(point, camera) {
  return { x: point.x - camera.x, y: point.y - camera.y };
}

export function sceneToPage(point, camera) {
  return { x: point.x + camera.x, y: point.y + camera.y };
}

export function pageToScreen(point, camera) {
  const scene = pageToScene(point, camera);
  return { x: scene.x * camera.z, y: scene.y * camera.z };
}

export function screenToPage(point, camera) {
  return sceneToPage({ x: point.x / camera.z, y: point.y / camera.z }, camera);
}

/**
 * an orthographic frustum measured in scene units, so a 3d element keeps its size relative to the
 * sketch beside it no matter how far the board is zoomed out. this is the whole trick: zoom is
 * baked into the frustum, never into the object's scale, so nothing in the scene has to know.
 */
export function orthoFrustum(camera, viewport, near = -10000, far = 10000) {
  return {
    left: 0,
    right: viewport.w / camera.z,
    top: 0,
    bottom: viewport.h / camera.z,
    near,
    far,
  };
}

/**
 * css for a plain DOM overlay pinned to a page position, for the things that are cheaper as html
 * than as geometry: a label, a caption, a slider handle.
 */
export function cssTransform(camera, pagePoint, extra = 0) {
  const screen = pageToScreen(pagePoint, camera);
  return `translate(${screen.x.toFixed(3)}px, ${screen.y.toFixed(3)}px) scale(${(camera.z * (1 + extra)).toFixed(6)})`;
}

/**
 * whether two layers agree, for a dev overlay that should not need a screenshot to answer.
 * returns the screen-space error of the four corners, in css pixels.
 */
export function disagreement(camera, viewport) {
  const page = visiblePage(camera, viewport);
  const corners = [
    { x: page.x, y: page.y },
    { x: page.x + page.w, y: page.y },
    { x: page.x, y: page.y + page.h },
    { x: page.x + page.w, y: page.y + page.h },
  ];
  const want = [
    { x: 0, y: 0 },
    { x: viewport.w, y: 0 },
    { x: 0, y: viewport.h },
    { x: viewport.w, y: viewport.h },
  ];
  return corners.map((corner, index) => {
    const got = pageToScreen(corner, camera);
    return Math.hypot(got.x - want[index].x, got.y - want[index].y);
  });
}
