/**
 * font.test.mjs: handwriting in, a font out, and the font is checked by drawing it.
 *
 * counting contours proved nothing here. the first version of this pipeline had the right number
 * of contours in every glyph and still drew every O as a disc, because upstream fontasy winds a
 * hole the same way as the shape around it and the fill rule then paints it solid. so these tests
 * rasterise the built font and count ink islands and holes in the picture, which is the only
 * thing a person looking at the font would be able to see.
 *
 * the fixtures are made by drawing a real typeface onto a page (tests/fixtures/*.png), so every
 * expected shape is known in advance and none of it is borrowed from the code being tested.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import opentype from "opentype.js";
import * as fp from "../src/font/pipeline.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const load = (name) => {
  const p = PNG.sync.read(fs.readFileSync(path.join(here, "fixtures", `${name}.png`)));
  return { rgba: p.data, width: p.width, height: p.height };
};
const slice = (u) => u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength);

// --- a small rasteriser, so the tests need nothing but node ---------------------------------

/** fill a glyph into a grid with the non-zero winding rule, as a real renderer does. */
function raster(glyph, size = 160) {
  const scale = size / 1000, ox = 20, oy = size * 0.85 + 10;
  const W = size + 40, H = size + 40;
  const edges = [];
  let cur = null, start = null;
  const P = (x, y) => [ox + x * scale, oy - y * scale];
  const flatten = (p0, p1, p2, p3) => {
    const out = [];
    const n = 12;
    for (let i = 1; i <= n; i++) {
      const t = i / n, u = 1 - t;
      out.push([
        u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
        u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
      ]);
    }
    return out;
  };
  const line = (a, b) => { if (a[1] !== b[1]) edges.push([a, b]); };
  for (const c of glyph.path.commands) {
    if (c.type === "M") { cur = P(c.x, c.y); start = cur; }
    else if (c.type === "L") { const n = P(c.x, c.y); line(cur, n); cur = n; }
    else if (c.type === "C") {
      for (const q of flatten(cur, P(c.x1, c.y1), P(c.x2, c.y2), P(c.x, c.y))) { line(cur, q); cur = q; }
    } else if (c.type === "Z") { line(cur, start); cur = start; }
  }
  const grid = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) {
    const yc = y + 0.5, hits = [];
    for (const [a, b] of edges) {
      const lo = Math.min(a[1], b[1]), hi = Math.max(a[1], b[1]);
      if (yc < lo || yc >= hi) continue;
      hits.push([a[0] + ((yc - a[1]) / (b[1] - a[1])) * (b[0] - a[0]), b[1] > a[1] ? 1 : -1]);
    }
    hits.sort((p, q) => p[0] - q[0]);
    let wind = 0;
    for (let i = 0; i < hits.length - 1; i++) {
      wind += hits[i][1];
      if (wind !== 0) {
        for (let x = Math.ceil(hits[i][0] - 0.5); x < hits[i + 1][0] - 0.5; x++) if (x >= 0 && x < W) grid[y * W + x] = 1;
      }
    }
  }
  return { grid, W, H };
}

/** count 8-connected regions of `val` in a grid. */
function regions(grid, W, H, val) {
  const seen = new Uint8Array(W * H);
  let n = 0;
  for (let i = 0; i < grid.length; i++) {
    if (grid[i] !== val || seen[i]) continue;
    n++;
    const st = [i];
    seen[i] = 1;
    while (st.length) {
      const k = st.pop(), x = k % W, y = (k - x) / W;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const ni = ny * W + nx;
        if (grid[ni] === val && !seen[ni]) { seen[ni] = 1; st.push(ni); }
      }
    }
  }
  return n;
}

/** what a person sees: separate pieces of ink, and enclosed holes in them. */
function look(font, ch) {
  const { grid, W, H } = raster(font.charToGlyph(ch));
  return { islands: regions(grid, W, H, 1), holes: regions(grid, W, H, 0) - 1 };
}

// --- one real run, shared by the shape tests ------------------------------------------------

const built = await fp.sheetToFont(opentype, load("sheet"), { family: "Test Hand" });
const font = opentype.parse(slice(built.files.otf));

test("a clean 26/26/10 sheet becomes a complete 62-character font", () => {
  assert.equal(built.meta.glyphs, 62);
  assert.equal(built.meta.complete, true);
  assert.deepEqual([built.meta.caps, built.meta.lower, built.meta.digits], [26, 26, 10]);
  assert.equal(built.meta.codepoints.length, 62);
});

test("the bytes parse back as a font with the family name that was asked for", () => {
  assert.equal(font.names.fontFamily.en, "Test Hand");
  assert.equal(font.unitsPerEm, 1000);
  assert.ok(font.glyphs.length >= 62);
});

test("every character maps to a glyph that has ink in it", () => {
  const blank = built.meta.codepoints.map((c) => String.fromCodePoint(c)).filter((ch) => look(font, ch).islands === 0);
  assert.deepEqual(blank, []);
});

test("counters are open: each of these has exactly one hole", () => {
  // the first build of this pipeline failed exactly this. upstream winds a counter the same way
  // as the letter around it, and the non-zero rule paints it solid.
  for (const ch of "OAoe0agdPQDRbpq694") assert.equal(look(font, ch).holes, 1, `${ch} should have one counter`);
});

test("B and 8 have two holes", () => {
  assert.equal(look(font, "B").holes, 2);
  assert.equal(look(font, "8").holes, 2);
});

test("letters without a counter stay solid", () => {
  for (const ch of "IlEFLTHUVWXYZckmnrsuvwxyz") assert.equal(look(font, ch).holes, 0, `${ch} should have no hole`);
});

test("i and j keep their dots, which upstream dropped", () => {
  assert.equal(look(font, "i").islands, 2);
  assert.equal(look(font, "j").islands, 2);
  assert.equal(look(font, "l").islands, 1);
});

test("a wide letter is wider than a narrow one, so the metrics came from the drawing", () => {
  assert.ok(font.charToGlyph("W").advanceWidth > font.charToGlyph("i").advanceWidth + 200);
});

test("a hole winds opposite to its outline, which is the whole reason counters render", () => {
  const dir = (pts) => {
    let a = 0;
    for (let i = 0; i < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
      a += x1 * y2 - x2 * y1;
    }
    return Math.sign(a);
  };
  const subs = [];
  let cur = null;
  for (const c of font.charToGlyph("O").path.commands) {
    if (c.type === "M") { cur = [[c.x, c.y]]; subs.push(cur); }
    else if (c.x !== undefined) cur.push([c.x, c.y]);
  }
  assert.equal(subs.length, 2);
  assert.notEqual(dir(subs[0]), dir(subs[1]));
});

// --- the things upstream did quietly ---------------------------------------------------------

test("a row with one letter missing is refused, naming the row and the count", () => {
  const detected = fp.detect(load("sheet_missing_F"));
  const problems = fp.check(detected);
  assert.equal(problems.length, 1);
  assert.deepEqual([problems[0].row, problems[0].found, problems[0].needed], [1, 25, 26]);
  assert.match(problems[0].reason, /misnamed/);
  assert.throws(() => fp.trace(detected), (e) => e instanceof fp.FontRefused && /25 glyphs, not 26/.test(e.message));
});

test("touching letters merge, and the refusal says a neighbour absorbed one", () => {
  const problems = fp.check(fp.detect(load("sheet_touching")));
  assert.equal(problems.length, 1);
  assert.equal(problems[0].found, 25);
  assert.match(problems[0].reason, /merged into a neighbour/);
});

test("allowPartial keeps the good rows and reports the skipped glyphs", () => {
  const traced = fp.trace(fp.detect(load("sheet_missing_F")), { allowPartial: true });
  assert.equal(traced.glyphs.length, 36); // lowercase 26 + digits 10, no caps
  assert.equal(traced.skipped.length, 25); // the 25 capitals that could not be named
  assert.ok(traced.glyphs.every((g) => g.type !== "caps"));
});

test("a partial font reports what it covers, so the dashboard can say partial", async () => {
  const traced = fp.trace(fp.detect(load("sheet_missing_F")), { allowPartial: true });
  const out = await fp.build(opentype, traced.glyphs, { family: "Partial" });
  assert.equal(out.meta.complete, false);
  assert.deepEqual([out.meta.caps, out.meta.lower, out.meta.digits], [0, 26, 10]);
});

test("woff2 is refused, because exporting a woff under that name would be a lie", async () => {
  await assert.rejects(
    fp.build(opentype, fp.trace(fp.detect(load("sheet"))).glyphs, { formats: ["woff2"] }),
    (e) => e instanceof fp.FontRefused && /woff2 needs brotli/.test(e.message),
  );
});

test("an unknown format is refused with the list of what is available", async () => {
  await assert.rejects(
    fp.build(opentype, fp.trace(fp.detect(load("sheet"))).glyphs, { formats: ["eot"] }),
    (e) => /otf, ttf, woff/.test(e.message),
  );
});

test("a font with no family name is refused", async () => {
  await assert.rejects(fp.build(opentype, fp.trace(fp.detect(load("sheet"))).glyphs, { family: "  " }), /family name/);
});

test("pixels of the wrong length are refused before anything runs", () => {
  assert.throws(() => fp.detect({ rgba: new Uint8Array(10), width: 100, height: 100 }), /needs 40000/);
});

test("a blank page finds nothing and says what to try", () => {
  const w = 200, h = 200, rgba = new Uint8Array(w * h * 4).fill(255);
  assert.throws(() => fp.detect({ rgba, width: w, height: h }), /no glyphs found.*invert/);
});

test("the same sheet gives the same font twice", async () => {
  const again = await fp.sheetToFont(opentype, load("sheet"), { family: "Test Hand" });
  assert.deepEqual(Buffer.from(again.files.otf), Buffer.from(built.files.otf));
});

test("a build a second later is byte-identical, so a sheet files as one artifact and not many", async () => {
  await new Promise((r) => setTimeout(r, 1100));
  const later = await fp.sheetToFont(opentype, load("sheet"), { family: "Test Hand" });
  assert.deepEqual(Buffer.from(later.files.otf), Buffer.from(built.files.otf));
  assert.deepEqual(Buffer.from(later.files.woff), Buffer.from(built.files.woff));
});

test("freezing the date keeps the checksums valid: the whole-file sum lands on the sfnt magic number", () => {
  const b = built.files.otf;
  let sum = 0;
  for (let i = 0; i < b.length; i += 4) {
    sum = (sum + (((b[i] ?? 0) << 24 | (b[i + 1] ?? 0) << 16 | (b[i + 2] ?? 0) << 8 | (b[i + 3] ?? 0)) >>> 0)) >>> 0;
  }
  assert.equal(sum, 0xB1B0AFBA);
});

test("the woff is smaller than the otf it wraps and starts with the wOFF signature", () => {
  assert.ok(built.files.woff.length < built.files.otf.length);
  assert.deepEqual([...built.files.woff.slice(0, 4)], [0x77, 0x4f, 0x46, 0x46]);
});
