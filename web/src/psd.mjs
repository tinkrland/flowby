/**
 * psd.mjs: a photoshop document as a layer tree, and what of it reaches the board.
 *
 * the walk is ported from the owner's own repo `arsoninstigator/bridgette` (`designs/src/porter/parse.ts`,
 * `walkPsdLayer` and `psdKind`), because that file already answers the two questions worth answering
 * about a layered document: what is in it, and what a person is allowed to change. its `policy` and
 * `editable` flags are kept, since a layer that arrives looking editable and is not is worse than one
 * that says it is locked.
 *
 * what is ours is `boardPlan`: bridgette's job ends at producing a file, and flowby's job is deciding
 * which layers become elements on a board and which are only counted. a group is not an element, and a
 * hidden layer is not drawn, and both of those are decisions rather than accidents.
 */

/** layers a psd can hold, in the vocabulary this tree already uses. */
export const KINDS = Object.freeze(["text", "image", "shape", "group", "other"]);

/** what may be changed about a layer once it is on the board. */
export const POLICY = Object.freeze({
  locked: "drawn as it arrived: pixels, and nothing here can re-render them",
  partial: "some of it is editable: what the flags below allow",
  customizable: "the layer is rebuilt here, so text, fills and placement are all editable",
});

/** psd hidden flag, text presence and children, in bridgette's order. */
export function psdKind(layer) {
  if (layer?.text) return "text";
  if (Array.isArray(layer?.children) && layer.children.length > 0) return "group";
  if (layer?.canvas || layer?.imageData) return "image";
  return "shape";
}

/** the effects a layer declares, named rather than counted, so the panel can list them. */
export function effectsOf(layer) {
  const out = [];
  if (!layer?.effects) return out;
  for (const [name, value] of Object.entries(layer.effects)) {
    if (value && (Array.isArray(value) ? value.length > 0 : true)) out.push(name);
  }
  return out;
}

/**
 * the layer tree, in reading order, with paths and depths.
 *
 * @param {any} psd the object `readPsd` returns
 */
export function psdLayers(psd) {
  const layers = [];
  const roots = [];
  let n = 0;
  const walk = (layer, parentPath, depth) => {
    const id = `psd-${n++}`;
    const name = layer?.name || "layer";
    const path = parentPath ? `${parentPath}/${name}` : name;
    const kind = psdKind(layer);
    const effects = effectsOf(layer);
    layers.push({
      id,
      name,
      path,
      depth,
      kind,
      visible: !layer?.hidden,
      effects,
      // bridgette marks a parsed layer `locked` with no flags set, and that is the truthful default:
      // nothing about a raster layer is rebuilt here until something says it is.
      policy: "locked",
      editable: {},
      text: layer?.text?.text ?? null,
      opacity: typeof layer?.opacity === "number" ? layer.opacity / 255 : null,
      blendMode: layer?.blendMode ?? null,
      box: {
        left: layer?.left ?? null,
        top: layer?.top ?? null,
        width: Number.isFinite(layer?.right) && Number.isFinite(layer?.left) ? layer.right - layer.left : null,
        height: Number.isFinite(layer?.bottom) && Number.isFinite(layer?.top) ? layer.bottom - layer.top : null,
      },
      children: [],
      // the object ag-psd handed back, kept so the host can take a layer's canvas without walking the
      // raw tree a second time and hoping the two walks agree on order
      raw: layer,
    });
    const made = layers[layers.length - 1];
    if (Array.isArray(layer?.children)) {
      for (const child of layer.children) made.children.push(walk(child, path, depth + 1));
    }
    return id;
  };
  for (const child of psd?.children ?? []) roots.push(walk(child, "", 0));
  return { layers, roots, width: psd?.width ?? null, height: psd?.height ?? null };
}

/**
 * a box is usable when the layer has a place. the four numbers are not equal citizens: ag-psd restores a
 * text layer's left and top and returns right and bottom equal to them, so a text layer has an extent of
 * zero and the host measures the words itself. a layer drawn as pixels needs a real size; a text layer
 * only needs somewhere to start.
 */
const placed = (layer) => Number.isFinite(layer.box.left) && Number.isFinite(layer.box.top);
const sized = (layer) => Number.isFinite(layer.box.width) && layer.box.width > 0
  && Number.isFinite(layer.box.height) && layer.box.height > 0;

/**
 * which layers become elements, and what is left behind, counted.
 *
 * a group is not an element and a hidden layer is not drawn, so neither is placed; both are counted so
 * the panel can say "3 of 5" instead of quietly importing two thirds of a document. a shape layer is
 * not placed either: this tree has no vector element that a psd's path data would survive into, and
 * placing an empty box would be a promise about pixels that do not exist.
 *
 * @param {ReturnType<typeof psdLayers>} tree
 */
export function boardPlan(tree) {
  const place = [];
  const skipped = { hidden: 0, group: 0, shape: 0, boxless: 0 };
  const withEffects = [];
  for (const layer of tree?.layers ?? []) {
    if (layer.kind === "group") { skipped.group += 1; continue; }
    if (!layer.visible) { skipped.hidden += 1; continue; }
    if (layer.kind === "shape") { skipped.shape += 1; continue; }
    if (!placed(layer) || (layer.kind === "image" && !sized(layer))) { skipped.boxless += 1; continue; }
    if (layer.effects.length > 0) withEffects.push(layer.name);
    place.push({
      id: layer.id,
      name: layer.name,
      kind: layer.kind,
      x: layer.box.left,
      y: layer.box.top,
      // null, not zero: a text layer's size is not in the file, and the host measures it
      w: sized(layer) ? layer.box.width : null,
      h: sized(layer) ? layer.box.height : null,
      text: layer.kind === "text" ? layer.text : null,
      path: layer.path,
      effects: layer.effects,
      // the place entry carries the layer so a host can take its pixels without a second lookup
      raw: layer.raw,
      opacity: layer.opacity,
      blendMode: layer.blendMode,
    });
  }
  const total = (tree?.layers ?? []).length;
  const notes = [];
  if (skipped.hidden) notes.push(`${skipped.hidden} hidden`);
  if (skipped.group) notes.push(`${skipped.group} group${skipped.group === 1 ? "" : "s"}`);
  if (skipped.shape) notes.push(`${skipped.shape} vector layer${skipped.shape === 1 ? "" : "s"} not drawn`);
  if (skipped.boxless) notes.push(`${skipped.boxless} without a place on the canvas`);
  if (withEffects.length) notes.push(`${withEffects.length} with effects, which are not rebuilt`);
  return {
    place,
    skipped,
    withEffects,
    total,
    summary: total === 0 ? "the document holds no layers" : `${place.length} of ${total} layer${total === 1 ? "" : "s"} placed${notes.length ? `: ${notes.join(", ")}` : ""}`,
  };
}

/**
 * what each format costs, said before it is read.
 *
 * the psd line is the one that matters: an imported document arrives as pixels in place, not as a file
 * this tree can write back. bridgette's own notes say the same thing about its writers, and a promise
 * to round-trip a psd would be the one claim nothing here can keep.
 */
export const FIDELITY = Object.freeze({
  psd: "layers arrive as placed pixels. nothing here writes a psd back, so effects, adjustment layers and masks are not rebuilt",
  figma: "frames arrive as rendered images at a chosen scale; the layer tree is read for names and boxes",
  ai: "read for layer names only. export a png or svg and drop that for pixels",
  eps: "read for layer names only. export a png or svg and drop that for pixels",
});
