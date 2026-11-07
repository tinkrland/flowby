/**
 * pipeline.mjs: handwriting in, a font out, with every silent failure turned into a refusal.
 *
 * `vendor.mjs` is fontasy's own numeric core. this file is what flowby adds: it takes pixels
 * instead of reading a canvas, takes sliders as arguments instead of reading the page, and says
 * out loud the three things the original did quietly.
 *
 * the three quiet failures, each read from fontasy's source and each reproduced by a test here:
 *
 *   1. labels are positional and all-or-nothing. a row is labelled A..Z only if it holds exactly
 *      26 glyphs, 0..9 only if exactly 10. one merged or missed letter and the whole row gets
 *      placeholder names (C01, c01, #01), and the exporter then skips every glyph whose label is
 *      not a single character. the result is a font with no letters and no error. here that is a
 *      refusal that names the row, the count it found, and the count it needed.
 *
 *   2. woff2 is offered and not delivered. the button exports a .woff and says so in a status line
 *      that is gone a moment later. here `formats` never contains woff2, and asking for it is
 *      refused instead of substituted.
 *
 *   3. the exporter will happily write a font from whatever survived. here a font is only
 *      produced if the glyph set meets `minimum`, and what it covers is reported back, so a sheet
 *      with only uppercase is a partial font that says so.
 *
 * no DOM, no canvas, no globals beyond what node 24 and every browser already have. the caller
 * supplies `opentype` (the page loads it from a CDN, a worker bundles it, a test imports it).
 */

import * as core from "./vendor.mjs";

export class FontRefused extends Error {}

// the same defaults fontasy's own sliders open on, so a default run matches the original's.
export const DEFAULTS = Object.freeze({
  blur: 1,          // gaussian sigma; 0 turns it off
  threshold: null,  // null = otsu, a number 0..255 forces it
  invert: false,    // true when the ink is lighter than the paper
  dilate: 1,        // radius used only to join broken strokes before labelling
  minSize: 0.0002,  // smallest blob, as a share of the image area
  maxSize: 0.2,     // largest blob, as a share of the image area
  epsilon: 1.5,     // douglas-peucker tolerance when tracing outlines
});

export const FORMATS = Object.freeze(["otf", "ttf", "woff"]);

const UPM = 1000, ASCENDER = 800, DESCENDER = -200, SIDE_BEARING = 55;

// what a row of each type must hold for its glyphs to be named. this is fontasy's own rule.
export const ROW_SIZE = Object.freeze({ caps: 26, lower: 26, number: 10 });
const TYPES = ["caps", "lower", "number", "symbol"];

const NAMES = {
  caps: (i) => String.fromCharCode(65 + i),
  lower: (i) => String.fromCharCode(97 + i),
  number: (i) => String(i),
};


/**
 * attach a dot, tittle or accent to the letter it belongs to, by where it sits and not by how big it is.
 *
 * upstream `mergeFragments` joins a blob to its neighbour only if the blob's area is under 18% of
 * the 40th-percentile blob area. a dot of 135 px against a threshold of ~119 px stays loose, and
 * whether an i keeps its dot then depends on how big the other letters happen to be. measured on a
 * clean sheet: the dot was dropped, the i came out dotless, and so did the j. handwriting varies far
 * more than a typeface does, so a size rule is a coin toss.
 *
 * the geometric rule: a blob much smaller than a larger one, overlapping it horizontally, and
 * within a short vertical distance of it, is part of it. this runs first; upstream's merge still
 * runs after it for the cases it already handles.
 */
function attachMarks(comps, { smallRatio = 0.35, gapRatio = 0.6 } = {}) {
  if (comps.length < 2) return comps;
  const order = [...comps].sort((a, b) => b.area - a.area);
  const used = new Set(), out = [];
  for (const big of order) {
    if (used.has(big)) continue;
    let c = { ...big };
    for (const small of order) {
      if (small === big || used.has(small) || small.area >= big.area * smallRatio) continue;
      const overlap = Math.min(c.x + c.w, small.x + small.w) - Math.max(c.x, small.x);
      if (overlap < Math.min(small.w, c.w) * 0.5) continue;          // not above or below it
      const gap = small.y < c.y ? c.y - (small.y + small.h) : small.y - (c.y + c.h);
      if (gap > c.h * gapRatio) continue;                              // too far to belong to it
      const x1 = Math.min(c.x, small.x), y1 = Math.min(c.y, small.y);
      c = { x: x1, y: y1, w: Math.max(c.x + c.w, small.x + small.w) - x1, h: Math.max(c.y + c.h, small.y + small.h) - y1, area: c.area + small.area };
      used.add(small);
    }
    used.add(big); out.push(c);
  }
  return out;
}


/**
 * stamp a font with a fixed date, so the same sheet always makes the same bytes.
 *
 * opentype.js writes `modified` as the current time, always, and offers no option to stop it. two
 * builds a second apart then differ in four bytes, and flowby names an artifact by the hash of its
 * bytes, so one handwriting sheet would file as a new artifact every time it was run. this rewrites
 * the head table's created and modified fields to a fixed instant and recomputes the two checksums
 * that depend on them (the head table's entry in the directory, and checkSumAdjustment), so the
 * result still passes a strict loader.
 */
const FIXED_TIME = 3913056000; // 2024-01-01T00:00:00Z in seconds since 1904, the sfnt epoch

function sum32(bytes, start, length) {
  let sum = 0;
  const end = start + Math.ceil(length / 4) * 4;
  for (let i = start; i < end; i += 4) {
    const w = ((bytes[i] ?? 0) << 24 | (bytes[i + 1] ?? 0) << 16 | (bytes[i + 2] ?? 0) << 8 | (bytes[i + 3] ?? 0)) >>> 0;
    sum = (sum + w) >>> 0;
  }
  return sum;
}

export function freezeTimestamps(input) {
  const bytes = new Uint8Array(input);
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = dv.getUint16(4);
  let entry = -1;
  for (let i = 0; i < count; i++) {
    const at = 12 + i * 16;
    if (String.fromCharCode(bytes[at], bytes[at + 1], bytes[at + 2], bytes[at + 3]) === "head") entry = at;
  }
  if (entry < 0) throw new FontRefused("the font has no head table, so it cannot be stamped");
  const offset = dv.getUint32(entry + 8), length = dv.getUint32(entry + 12);
  dv.setUint32(offset + 8, 0);                       // checkSumAdjustment, recomputed below
  dv.setUint32(offset + 20, 0); dv.setUint32(offset + 24, FIXED_TIME);   // created (64-bit)
  dv.setUint32(offset + 28, 0); dv.setUint32(offset + 32, FIXED_TIME);   // modified (64-bit)
  dv.setUint32(entry + 4, sum32(bytes, offset, length));                 // head's directory checksum
  const total = sum32(bytes, 0, bytes.length);
  dv.setUint32(offset + 8, (0xB1B0AFBA - total) >>> 0);                  // the whole-file adjustment
  return bytes;
}

/** find the glyphs on a sheet. `rgba` is width*height*4 bytes, exactly what getImageData returns. */
export function detect({ rgba, width, height }, options = {}) {
  const o = { ...DEFAULTS, ...options };
  if (!rgba || rgba.length !== width * height * 4) {
    throw new FontRefused(`the pixels are ${rgba ? rgba.length : 0} bytes, and a ${width}x${height} image needs ${width * height * 4}`);
  }
  let gray = core.toGray(rgba, width * height);
  if (o.blur > 0) gray = core.gaussianBlur(gray, width, height, o.blur);
  const threshold = o.threshold == null ? core.otsu(gray) : o.threshold;
  const binary = new Uint8Array(width * height);
  for (let i = 0; i < gray.length; i++) binary[i] = (o.invert ? gray[i] > threshold : gray[i] < threshold) ? 1 : 0;
  const joined = o.dilate > 0 ? core.dilate(binary, width, height, o.dilate) : binary;
  const area = width * height;
  // keep small blobs as candidates first. upstream filtered by area before merging, which threw
  // away every dot (135 px against a 256 px floor) before anything could attach it. a blob that is
  // still loose after attaching is a speck, and is dropped then, by the same floor upstream used.
  const speck = o.minSize * area, tiny = Math.max(4, speck * 0.05);
  const all = core.labelComps(joined, width, height).filter((c) => c.area >= tiny && c.area <= o.maxSize * area);
  const attached = attachMarks(all);
  let comps = attached.filter((c) => c.area >= speck);
  comps = core.mergeFragments(comps);
  const rows = core.groupRows(comps);
  if (!rows.length) {
    throw new FontRefused("no glyphs found. raise the threshold, or turn invert on if the ink is lighter than the paper");
  }
  const types = core.autoClassify(rows);
  return {
    width, height, threshold, binary,
    rows: rows.map((chars, i) => ({ chars, type: types[i] || "caps", count: chars.length })),
  };
}

/** say, per row, whether its glyphs can be named. returns the problems; empty means nameable. */
export function check(detected, rowTypes = null) {
  const problems = [];
  detected.rows.forEach((row, i) => {
    const type = rowTypes ? rowTypes[i] : row.type;
    if (type === "skip" || type === "symbol") return;
    const want = ROW_SIZE[type];
    if (want && row.count !== want) {
      const gap = row.count - want;
      problems.push({
        row: i + 1, type, found: row.count, needed: want,
        reason: `row ${i + 1} is read as ${type} and holds ${row.count} glyphs, not ${want}. ` +
          (gap < 0
            ? `${-gap} ${-gap === 1 ? "is" : "are"} missing or merged into a neighbour, so every letter after the gap would be misnamed`
            : `${gap} extra ${gap === 1 ? "mark was" : "marks were"} found (a speck, a dotted i, or a letter split in two)`),
      });
    }
  });
  return problems;
}


/**
 * trace a glyph with every ink island in its box, not only the first one found.
 *
 * upstream `glyphToVectorPath` starts at the first ink pixel, walks one outer boundary, and then
 * looks for holes inside it. a dot separated from its stem is a second outer boundary, which it
 * never walks, so i, j, ! ? : ; and any letter written in two strokes lose a part. the dot IS found
 * and merged into the glyph's box by mergeFragments, and then dropped at tracing. measured on a
 * clean 26/26/10 sheet: both i and j came out dotless.
 *
 * this labels the islands in the glyph's own box and runs upstream's tracer once per island, then
 * joins the paths. holes are found per island by the same flood fill upstream uses.
 */
function traceAll(binary, bounds, fw, epsilon) {
  const { x, y, w, h } = bounds;
  const pad = 2, lw = w + 2 * pad, lh = h + 2 * pad;
  const local = new Uint8Array(lw * lh);
  for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) local[(dy + pad) * lw + (dx + pad)] = binary[(y + dy) * fw + (x + dx)];
  const seen = new Uint8Array(lw * lh);
  const islands = [];
  for (let i = 0; i < local.length; i++) {
    if (!local[i] || seen[i]) continue;
    const stack = [i]; seen[i] = 1;
    let x1 = lw, y1 = lh, x2 = 0, y2 = 0, area = 0;
    while (stack.length) {
      const k = stack.pop(), kx = k % lw, ky = (k - kx) / lw;
      area++; if (kx < x1) x1 = kx; if (kx > x2) x2 = kx; if (ky < y1) y1 = ky; if (ky > y2) y2 = ky;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = kx + dx, ny = ky + dy; if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue;
        const ni = ny * lw + nx; if (local[ni] && !seen[ni]) { seen[ni] = 1; stack.push(ni); }
      }
    }
    islands.push({ x1, y1, x2, y2, area, seed: i });
  }
  // an island of a pixel or two inside a glyph box is a speck, not a dot. a dot is a real shape.
  const minIsland = Math.max(6, Math.round(0.02 * Math.max(...islands.map((s) => s.area), 0)));
  const real = islands.filter((s) => s.area >= minIsland);
  if (!real.length) return null;
  const parts = [];
  for (const isl of real) {
    // give upstream a copy that holds only this island, so its single-boundary walk sees one shape
    const only = new Uint8Array(lw * lh);
    const st = [isl.seed]; const mark = new Uint8Array(lw * lh); mark[isl.seed] = 1;
    while (st.length) {
      const k = st.pop(); only[k] = 1; const kx = k % lw, ky = (k - kx) / lw;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = kx + dx, ny = ky + dy; if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue;
        const ni = ny * lw + nx; if (local[ni] && !mark[ni]) { mark[ni] = 1; st.push(ni); }
      }
    }
    const outer = core.mooreTrace(only, lw, lh, isl.seed % lw, Math.floor(isl.seed / lw));
    if (outer.length < 3) continue;
    const norm = (pts) => pts.map(([cx, cy]) => [cx - pad, cy - pad]);
    let path = core.polyToBezierPath(norm(core.simplify(outer, epsilon)));
    const reached = core.floodFillBg(only, lw, lh);
    for (const hole of core.findHoles(only, lw, lh, reached)) {
      const sh = core.simplify(hole, epsilon); if (sh.length < 3) continue;
      // reversed on purpose. upstream walks every boundary the same way round, so an outer ring and
      // its counter both come out clockwise, and the non-zero fill rule then paints the counter
      // solid: every O, B, 8, e and A upstream produces is a blob. a hole must wind opposite to
      // the shape that contains it. measured before this line: all contours of O, B, o, e, A same
      // direction; rendered, 0 holes in every one.
      path += " " + core.polyToBezierPath(norm(sh).reverse());
    }
    parts.push(path);
  }
  return parts.length ? parts.join(" ") : null;
}

/** trace every nameable glyph and give it its character. refuses before tracing if a row is wrong. */
export function trace(detected, { rowTypes = null, epsilon = DEFAULTS.epsilon, allowPartial = false } = {}) {
  const problems = check(detected, rowTypes);
  if (problems.length && !allowPartial) {
    const err = new FontRefused(problems.map((p) => p.reason).join("; "));
    err.problems = problems;
    throw err;
  }
  const glyphs = [];
  const skipped = [];
  detected.rows.forEach((row, i) => {
    const type = rowTypes ? rowTypes[i] : row.type;
    if (type === "skip") return;
    const want = ROW_SIZE[type];
    const nameable = want && row.count === want;
    row.chars.forEach((comp, idx) => {
      if (!nameable) { skipped.push({ row: i + 1, type, index: idx }); return; }
      const vectorPath = traceAll(detected.binary, comp, detected.width, epsilon);
      if (!vectorPath) { skipped.push({ row: i + 1, type, index: idx, reason: "no outline could be traced" }); return; }
      glyphs.push({
        char: NAMES[type](idx), type, vectorPath,
        bounds: { x: comp.x, y: comp.y, w: comp.w, h: comp.h },
      });
    });
  });
  if (!glyphs.length) throw new FontRefused("no glyph could be named, so there is nothing to put in a font");
  return { glyphs, skipped };
}

/** which codepoints a set of glyphs maps, and whether it clears the bar for a usable font. */
export function coverage(glyphs) {
  const codepoints = glyphs.map((g) => g.char.codePointAt(0)).sort((a, b) => a - b);
  const has = (re) => glyphs.filter((g) => re.test(g.char)).length;
  return {
    codepoints,
    caps: has(/[A-Z]/), lower: has(/[a-z]/), digits: has(/[0-9]/),
    complete: has(/[A-Z]/) === 26 && has(/[a-z]/) === 26 && has(/[0-9]/) === 10,
  };
}

/**
 * build the font. `opentype` is injected. returns the bytes of each format and what the font maps,
 * which is exactly what flowby's artifacts.file_artifact wants (family + codepoints).
 */
export async function build(opentype, glyphs, { family = "Handwriting", formats = ["otf", "ttf", "woff"], minimum = 1 } = {}) {
  const bad = formats.filter((f) => !FORMATS.includes(f));
  if (bad.length) {
    throw new FontRefused(
      bad.includes("woff2")
        ? "woff2 needs brotli, which is not available here, and substituting a .woff under that name would be a lie. ask for woff"
        : `${bad.join(", ")} is not a format this can write. it writes ${FORMATS.join(", ")}`,
    );
  }
  if (glyphs.length < minimum) throw new FontRefused(`${glyphs.length} glyphs is below the minimum of ${minimum}`);
  if (!family.trim()) throw new FontRefused("a font needs a family name, or every app will list it as Untitled");

  const caps = glyphs.filter((g) => g.type === "caps");
  const refH = caps.length ? Math.max(...caps.map((g) => g.bounds.h)) : Math.max(...glyphs.map((g) => g.bounds.h));
  const scale = refH > 0 ? ASCENDER / refH : 1;
  const OT = opentype;
  const list = [
    new OT.Glyph({ name: ".notdef", unicode: 0, advanceWidth: 500, path: new OT.Path() }),
    new OT.Glyph({ name: "space", unicode: 32, advanceWidth: 280, path: new OT.Path() }),
  ];
  for (const g of glyphs) {
    list.push(new OT.Glyph({
      name: g.char, unicode: g.char.codePointAt(0),
      advanceWidth: Math.max(Math.round(g.bounds.w * scale) + SIDE_BEARING * 2, 100),
      path: core.svgToOTPath(OT, g.vectorPath, scale, ASCENDER),
    }));
  }
  const font = new OT.Font({ familyName: family, styleName: "Regular", unitsPerEm: UPM, ascender: ASCENDER, descender: DESCENDER, glyphs: list });
  const sfnt = freezeTimestamps(font.toArrayBuffer()).buffer;
  const files = {};
  for (const f of formats) {
    if (f === "otf" || f === "ttf") files[f] = new Uint8Array(sfnt);
    else if (f === "woff") files[f] = new Uint8Array(await core.sfntToWoff(sfnt));
  }
  return { family, files, meta: { family, ...coverage(glyphs), glyphs: glyphs.length } };
}

/** the whole thing, for a caller that does not need the steps apart. */
export async function sheetToFont(opentype, image, options = {}) {
  const detected = detect(image, options);
  const traced = trace(detected, options);
  const built = await build(opentype, traced.glyphs, options);
  return { ...built, skipped: traced.skipped, rows: detected.rows.map((r) => ({ type: r.type, count: r.count })) };
}
