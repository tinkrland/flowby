/**
 * swatch.mjs: recolour an image to a palette, in the browser, with no model.
 *
 * ported from the owner's own Figma plugin `kqrla/swatchswap` (and its `-pro` fork), read on
 * 2026-11-13: the quantiser and the pixel blend below are that algorithm, with **its constants
 * unchanged** so a result here matches a result there. this is the honest answer to "vectary switches
 * colours with ai": theirs infers, this measures, and the difference is worth keeping in the words
 * rather than papering over with the word "ai".
 *
 * what is ours is `paletteMapping`: the plugin asks a person to pick each replacement by hand, and a
 * preset with one input and one job cannot. mapping every found colour to its nearest palette colour
 * is the same arithmetic, decided instead of typed.
 */

/** the plugin's numbers, named so a test can hold them still. */
export const QUANTIZE = Object.freeze({ alphaFloor: 30, mergeDistance: 30, maxColors: 8 });
export const APPLY = Object.freeze({ alphaFloor: 10, threshold: 35 });

export function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("")}`;
}

export function hexToRgb(hex) {
  const h = String(hex ?? "").replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null;
  return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16) };
}

const dist = (r1, g1, b1, r2, g2, b2) => Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);

/**
 * the distinct colours in an image, most frequent first.
 *
 * the plugin quantises to 5 bits a channel so that 16.7m colours become 32768 buckets, counts them,
 * then keeps a bucket only if it is at least `mergeDistance` away from every bucket already kept. that
 * greedy pass is why the list reads like a palette instead of like noise.
 *
 * @param {Uint8ClampedArray|number[]} rgba
 * @param {{maxColors?: number, alphaFloor?: number, mergeDistance?: number}} [options]
 */
export function quantize(rgba, options = {}) {
  const maxColors = options.maxColors ?? QUANTIZE.maxColors;
  const alphaFloor = options.alphaFloor ?? QUANTIZE.alphaFloor;
  const mergeDistance = options.mergeDistance ?? QUANTIZE.mergeDistance;
  const buckets = new Map();
  let visible = 0;
  for (let i = 0; i + 3 < rgba.length; i += 4) {
    const a = rgba[i + 3];
    if (a < alphaFloor) continue;
    visible += 1;
    const key = ((rgba[i] >> 3) << 10) | ((rgba[i + 1] >> 3) << 5) | (rgba[i + 2] >> 3);
    buckets.set(key, (buckets.get(key) ?? 0) + 1);
  }
  const sorted = [...buckets.entries()].sort((a, b) => b[1] - a[1]);
  const kept = [];
  for (const [key, count] of sorted) {
    if (kept.length >= maxColors) break;
    const r = ((key >> 10) & 0x1f) << 3;
    const g = ((key >> 5) & 0x1f) << 3;
    const b = (key & 0x1f) << 3;
    if (kept.some((p) => dist(r, g, b, p.r, p.g, p.b) < mergeDistance)) continue;
    kept.push({ r, g, b, count });
  }
  return {
    colours: kept.map((c) => ({ ...c, hex: rgbToHex(c), share: visible === 0 ? 0 : c.count / visible })),
    visible,
  };
}

/**
 * replace matched colours, in place on a copy.
 *
 * the plugin's blend, not a swap: a pixel `d` away from a source colour keeps `1 - d/threshold` of
 * itself and takes `d/threshold` of the target. that is what keeps an antialiased edge an edge instead
 * of a jagged border, and it is why a recolour here looks like a paint job rather than a mask.
 *
 * @param {Uint8ClampedArray|number[]} rgba
 * @param {{from: {r: number, g: number, b: number}, to: {r: number, g: number, b: number}}[]} mapping
 * @param {{threshold?: number, alphaFloor?: number}} [options]
 */
export function applySwatches(rgba, mapping, options = {}) {
  const threshold = options.threshold ?? APPLY.threshold;
  const alphaFloor = options.alphaFloor ?? APPLY.alphaFloor;
  const data = Uint8ClampedArray.from(rgba);
  const pairs = (mapping ?? []).filter((m) => m && m.from && m.to);
  let changed = 0;
  for (let i = 0; i + 3 < data.length; i += 4) {
    if (data[i + 3] < alphaFloor) continue;
    const pr = data[i], pg = data[i + 1], pb = data[i + 2];
    for (const pair of pairs) {
      const d = dist(pr, pg, pb, pair.from.r, pair.from.g, pair.from.b);
      if (d >= threshold) continue;
      const t = Math.max(0, 1 - d / threshold);
      data[i] = Math.round(pr * (1 - t) + pair.to.r * t);
      data[i + 1] = Math.round(pg * (1 - t) + pair.to.g * t);
      data[i + 2] = Math.round(pb * (1 - t) + pair.to.b * t);
      changed += 1;
      break;
    }
  }
  return { data, changed, total: Math.floor(data.length / 4) };
}

/**
 * what a preset can decide that a person would otherwise type: for each colour found, the nearest
 * colour in the palette. the metric is the plugin's own euclidean rgb, deliberately, so a mapping this
 * picks and a mapping a person picks from the same swatches are the same arithmetic.
 *
 * @param {{r: number, g: number, b: number}[]} colours
 * @param {string[]} palette hex strings
 */
export function paletteMapping(colours, palette) {
  const targets = (palette ?? []).map(hexToRgb).filter(Boolean);
  if (targets.length === 0) return [];
  return (colours ?? []).map((colour) => {
    let best = targets[0];
    let bestDistance = Infinity;
    for (const target of targets) {
      const d = dist(colour.r, colour.g, colour.b, target.r, target.g, target.b);
      if (d < bestDistance) { bestDistance = d; best = target; }
    }
    return { from: { r: colour.r, g: colour.g, b: colour.b }, to: { ...best }, distance: bestDistance };
  });
}
