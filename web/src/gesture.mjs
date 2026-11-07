/**
 * gesture.mjs: dropping and pasting onto the canvas, as decisions with no DOM.
 *
 * fuser's media intake is not a panel. a file dragged onto the bare canvas becomes a node, a file
 * dragged over a node tints it before release and replaces it on drop, and cmd/ctrl+v pastes what
 * is on the clipboard. the panel built on 2026-11-07 is still the right place for a figma link and
 * for a queue of files that need a look first, but it was the wrong centre of gravity for a single
 * image. this file is the other way in.
 *
 * everything here takes plain objects shaped like the browser's DataTransfer items and returns a
 * decision, so the rules (what counts as a file drag, when a paste belongs to a text field, which
 * node a drop lands on) are tested from node. `Canvas` events are wired to these in the skin.
 */

import * as intake from "./intake.mjs";

/** a drag carries files if the browser says so. text and links dragged around the page do not count. */
export function carriesFiles(types) {
  return Array.from(types || []).includes("Files");
}

/**
 * what a drag over the canvas should look like. `over` is the id of the node under the cursor, or
 * null for bare canvas. the answer is what to highlight, so the user sees the target before release.
 */
export function dragState({ types, over = null, nodes = {} }) {
  if (!carriesFiles(types)) return { active: false, target: null, verb: null };
  if (over && nodes[over]) {
    const node = nodes[over];
    return {
      active: true,
      target: over,
      verb: node.accepts ? `replace ${node.label}` : null,
      refuses: node.accepts ? null : `${node.label} does not take files`,
    };
  }
  return { active: true, target: null, verb: "add as new nodes" };
}

/**
 * where a drop lands. bare canvas creates nodes; a node that takes files replaces its content;
 * a node that does not take files refuses, and nothing is created behind the user's back.
 */
export function dropTarget({ over = null, nodes = {}, count = 1 }) {
  if (!over || !nodes[over]) return { action: "create", count };
  const node = nodes[over];
  if (!node.accepts) {
    return { action: "refuse", reason: `${node.label} does not take files. drop on the empty canvas to add a new node` };
  }
  if (count > 1) {
    return { action: "replace-first", node: over, extra: count - 1,
      note: `${node.label} takes one file, so the first replaces it and ${count - 1} more are added as new nodes` };
  }
  return { action: "replace", node: over };
}

/**
 * does this keyboard focus belong to something that types? pasting there is text, and a canvas that
 * stole it would break every text field on the page.
 */
export function typing(target) {
  if (!target) return false;
  const tag = String(target.tagName || "").toLowerCase();
  if (tag === "textarea") return true;
  if (tag === "input") {
    const t = String(target.type || "text").toLowerCase();
    return !["button", "checkbox", "radio", "range", "submit", "reset", "file", "image", "color"].includes(t);
  }
  return Boolean(target.isContentEditable);
}

/**
 * read a paste. a paste is a canvas import only if it carries files and the user is not typing.
 * returns the files to take, or why nothing was taken, so the skin can stay silent for ordinary text.
 */
export function readPaste({ files = [], hasText = false, target = null }) {
  if (typing(target)) return { take: [], why: "typing", silent: true };
  if (!files.length) return { take: [], why: hasText ? "text" : "empty", silent: true };
  return { take: files, why: "files", silent: false };
}

/**
 * a pasted screenshot has no name, so one is made up from the type and the time. two pastes in the
 * same second must not collide, or the second silently replaces the first in the queue.
 */
export function nameForPaste(file, index, now = new Date()) {
  if (file.name && file.name !== "image.png") return file.name;
  const ext = (file.type || "image/png").split("/")[1]?.replace("jpeg", "jpg") || "png";
  const stamp = now.toISOString().replace(/[:T]/g, "-").slice(0, 19);
  return `pasted-${stamp}-${index + 1}.${ext}`;
}

/**
 * lay new nodes out in a row, each as wide as its content asks for, left to right from where the
 * drop landed. this is the shape fuser's clip shows: a portrait is tall, a square is square, and
 * they sit side by side with a fixed gap and never overlap.
 */
export function layoutRow(items, { origin = { x: 0, y: 0 }, gap = 28, height = 220, max = 360 } = {}) {
  let x = origin.x;
  return items.map((item) => {
    const ratio = item.width && item.height ? item.width / item.height : 1;
    const w = Math.round(Math.min(max, Math.max(96, height * ratio)));
    const box = { x, y: origin.y, w, h: height };
    x += w + gap;
    return { ...item, box };
  });
}

/**
 * take what was dropped or pasted through the same classification the panel uses, and report every
 * file once: either an element to place or a refusal with its reason. nothing vanishes.
 */
export function takeFiles(files) {
  const placed = [], refused = [];
  for (const f of files) {
    try {
      const plan = intake.classify({ name: f.name, bytes: f.bytes });
      if (plan.via === "unpack") placed.push({ ...f, plan, needs: "unpack" });
      else placed.push({ ...f, plan, needs: null });
    } catch (e) {
      refused.push({ name: f.name, reason: e.message });
    }
  }
  return { placed, refused };
}
