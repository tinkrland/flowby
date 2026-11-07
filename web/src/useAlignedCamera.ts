/**
 * useAlignedCamera: the bridge between the two canvases, and the only file that knows both.
 *
 * tldraw owns the spatial layer and re-renders on every pan and zoom. the three.js scene has to
 * land on top of it, so its camera is recomputed from tldraw's on every frame rather than on
 * change events, because "almost aligned, one frame late" is exactly what makes a hybrid board feel
 * broken. all of the arithmetic lives in align.mjs, which has a test and no react in it; this file
 * is the subscription.
 *
 * state: designed. it typechecks against the versions in package.json and has never been built,
 * because this checkout has no node_modules. the maths it calls is verified.
 */

import { useFrame, useThree } from "@react-three/fiber";
import { useEditor } from "@tldraw/tldraw";
import { useMemo } from "react";

import { cameraFromTldraw, orthoFrustum, visiblePage } from "./align.mjs";

/** the size the container is currently drawn at, in css pixels. */
export function useViewportSize(ref) {
  const size = useMemo(() => ({ w: 1, h: 1 }), []);
  useFrame(() => {
    const box = ref.current?.getBoundingClientRect();
    if (box) {
      size.w = box.width;
      size.h = box.height;
    }
  });
  return size;
}

/**
 * keeps the orthographic camera glued to the board.
 *
 * the frustum carries the zoom, so nothing in the scene is ever scaled: a 12cm mesh next to a
 * 12cm sketch stays the same size when the board zooms. `y` points down here because page
 * coordinates do, and flipping it per object would be the bug that gets filed twice.
 */
export function useAlignedCamera(viewportRef) {
  const editor = useEditor();
  const { camera } = useThree();
  const viewport = useViewportSize(viewportRef);

  useFrame(() => {
    if (!editor || viewport.w <= 1) return;
    const own = cameraFromTldraw(editor.getCamera());
    const frustum = orthoFrustum(own, viewport);
    camera.left = frustum.left;
    camera.right = frustum.right;
    camera.top = frustum.top;
    camera.bottom = frustum.bottom;
    camera.near = frustum.near;
    camera.far = frustum.far;
    camera.updateProjectionMatrix();

    // the camera sits at the page origin of the scene, so `pageToScene` in align.mjs is the only
    // mapping an object needs: position at (x - own.x, y - own.y, z).
    camera.position.set(0, 0, 1000);
    camera.lookAt(0, 0, 0);
    void visiblePage(own, viewport);
  });

  return viewport;
}

/**
 * the two layers are separate DOM trees, and the inspector is a third subscriber. when the board
 * reconnects it replays, which is why toggling "inspect pipeline" costs one round trip and never a
 * rebuild of the scene: the graph did not change, only who is watching it.
 */
export function useBoardSocket(url, onMessage) {
  const open = () => {
    const socket = new WebSocket(url);
    socket.addEventListener("message", (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (error) {
        console.warn("flowby: dropped a message the board could not parse", error);
      }
    });
    return socket;
  };
  return { open };
}
