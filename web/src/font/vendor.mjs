/**
 * vendor.mjs: the numeric core of fontasy, lifted out of its web page.
 *
 * source: github.com/kqrla/fontasy (web/index.html, MIT, copyright 2026 fontasy). nothing here is
 * rewritten: these are the 18 functions that touch no DOM, copied as they were, with exactly one
 * change. `svgToOTPath` took `opentype` from a page global; it now takes it as its first argument
 * so the same code runs in a browser, a worker, or node. that is the whole reason this is a
 * vendored file and not a git submodule: the original is a single html page with its logic
 * inside a <script>, so there is nothing to import.
 *
 * what is NOT here is on purpose: the file picker, the zip reader, the classify ui, the sliders,
 * and the two download paths. flowby owns those, and `pipeline.mjs` drives this file instead.
 *
 * do not edit the functions below to fix a behaviour. wrap them in pipeline.mjs, so a diff
 * against upstream stays readable and a bug here can be reported to the repo it came from.
 */

// the two 8-neighbour direction tables the moore boundary tracer walks. upstream declares them
// at the top of its script, outside any function, which is why lifting only the functions
// missed them. they are the only top-level bindings the 18 functions below depend on.
const MDX = [-1, 0, 1, 1, 1, 0, -1, -1], MDY = [-1, -1, -1, 0, 1, 1, 1, 0];

function toGray(data, n) { const g = new Float32Array(n); for (let i = 0; i < n; i++) { const o = i * 4; g[i] = 0.299 * data[o] + 0.587 * data[o + 1] + 0.114 * data[o + 2] } return g }

function otsu(gray) {
  const hist = new Float64Array(256); for (const v of gray) hist[Math.min(255, Math.round(v))]++
  const n = gray.length; let tm = 0; for (let i = 0; i < 256; i++) tm += i * hist[i] / n
  let w0 = 0, m0 = 0, bv = 0, bt = 128
  for (let t = 0; t < 256; t++) { w0 += hist[t] / n; m0 += t * hist[t] / n; const w1 = 1 - w0; if (w0 < 1e-6 || w1 < 1e-6) continue; const v = w0 * w1 * ((m0 / w0) - ((tm - m0) / w1)) ** 2; if (v > bv) { bv = v; bt = t } }
  return bt
}

function gaussianBlur(gray, w, h, sigma) {
  if (sigma <= 0) return gray
  const kR = Math.max(1, Math.ceil(sigma * 2.5)), kSize = kR * 2 + 1, k = new Float32Array(kSize); let sum = 0
  for (let i = 0; i < kSize; i++) { const x = i - kR; k[i] = Math.exp(-(x * x) / (2 * sigma * sigma)); sum += k[i] }
  for (let i = 0; i < kSize; i++) k[i] /= sum
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { let v = 0; for (let i = 0; i < kSize; i++) v += gray[y * w + Math.max(0, Math.min(w - 1, x + i - kR))] * k[i]; tmp[y * w + x] = v }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { let v = 0; for (let i = 0; i < kSize; i++) v += tmp[Math.max(0, Math.min(h - 1, y + i - kR)) * w + x] * k[i]; out[y * w + x] = v }
  return out
}

function dilate(bin, w, h, r) {
  if (r <= 0) return bin; const out = new Uint8Array(w * h), r2 = r * r
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (bin[y * w + x]) { out[y * w + x] = 1; continue }; let f = false
    for (let dy = -r; dy <= r && !f; dy++) for (let dx = -r; dx <= r; dx++) { if (dx * dx + dy * dy > r2) continue; const nx = x + dx, ny = y + dy; if (nx >= 0 && ny >= 0 && nx < w && ny < h && bin[ny * w + nx]) { f = true; break } }
    out[y * w + x] = f ? 1 : 0
  }
  return out
}

function labelComps(bin, w, h) {
  const par = new Int32Array(w * h + 1); for (let i = 0; i < par.length; i++) par[i] = i
  function find(x) { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x] } return x }
  function unite(a, b) { a = find(a); b = find(b); if (a !== b) par[b] = a; return a }
  const lbl = new Int32Array(w * h); let nxt = 1
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const idx = y * w + x; if (!bin[idx]) continue
    const top = y > 0 ? find(lbl[(y - 1) * w + x]) : 0, left = x > 0 ? find(lbl[y * w + x - 1]) : 0
    if (!top && !left) lbl[idx] = nxt++; else if (top && !left) lbl[idx] = top; else if (!top && left) lbl[idx] = left; else lbl[idx] = unite(top, left)
  }
  const map = new Map()
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const l = lbl[y * w + x]; if (!l) continue; const r = find(l); lbl[y * w + x] = r; if (!map.has(r)) map.set(r, { x1: x, y1: y, x2: x, y2: y, area: 0 }); const c = map.get(r); if (x < c.x1) c.x1 = x; if (y < c.y1) c.y1 = y; if (x > c.x2) c.x2 = x; if (y > c.y2) c.y2 = y; c.area++ }
  return Array.from(map.values()).map(c => ({ x: c.x1, y: c.y1, w: c.x2 - c.x1 + 1, h: c.y2 - c.y1 + 1, area: c.area }))
}

function mergeFragments(comps) {
  if (comps.length < 2) return comps
  const sorted = [...comps].sort((a, b) => b.area - a.area); const medArea = sorted[Math.floor(sorted.length * 0.4)].area; const fragThresh = medArea * 0.18
  const used = new Uint8Array(sorted.length); const out = []
  for (let i = 0; i < sorted.length; i++) {
    if (used[i]) continue; let c = { ...sorted[i] }
    for (let j = i + 1; j < sorted.length; j++) {
      if (used[j] || sorted[j].area > fragThresh) continue; const d = sorted[j]
      const xG = Math.max(0, Math.max(d.x, c.x) - Math.min(d.x + d.w, c.x + c.w)), yG = Math.max(0, Math.max(d.y, c.y) - Math.min(d.y + d.h, c.y + c.h))
      if (xG < c.h * 0.55 && yG < c.h * 0.65) { const nx1 = Math.min(c.x, d.x), ny1 = Math.min(c.y, d.y); c = { x: nx1, y: ny1, w: Math.max(c.x + c.w, d.x + d.w) - nx1, h: Math.max(c.y + c.h, d.y + d.h) - ny1, area: c.area + d.area }; used[j] = 1 }
    }
    out.push(c); used[i] = 1
  }
  return out
}

function groupRows(chars) {
  if (!chars.length) return []; const sorted = [...chars].sort((a, b) => (a.y + a.h * .5) - (b.y + b.h * .5))
  const rows = [[sorted[0]]]
  for (let i = 1; i < sorted.length; i++) { const c = sorted[i], last = rows[rows.length - 1]; const avgMid = last.reduce((s, r) => s + r.y + r.h * .5, 0) / last.length; const avgH = last.reduce((s, r) => s + r.h, 0) / last.length; if (Math.abs((c.y + c.h * .5) - avgMid) > avgH * 0.55) rows.push([c]); else last.push(c) }
  return rows.map(r => r.sort((a, b) => a.x - b.x))
}

function autoClassify(rows) {
  function med(a) { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)] }
  const rowMedH = rows.map(r => med(r.map(c => c.h))); const allMedH = med(rowMedH)
  if (rows.length === 2 && rows[0].length >= 24 && rows[1].length >= 24) return ['caps', 'lower']
  return rows.map((row, ri) => { const n = row.length, ratio = rowMedH[ri] / allMedH; if (n <= 4) return 'symbol'; if (n === 10) return 'number'; if (ratio > 1.1) return 'caps'; if (ratio < 0.9) return 'lower'; return ri % 2 === 0 ? 'caps' : 'lower' })
}

function mooreDir(fx, fy, tx, ty) { const dx = Math.sign(tx - fx), dy = Math.sign(ty - fy); for (let d = 0; d < 8; d++) if (MDX[d] === dx && MDY[d] === dy) return d; return -1 }

function mooreTrace(bin, w, h, sx, sy) {
  if (!bin[sy * w + sx]) return []; const pts = [[sx, sy]]; let bx = sx - 1, by = sy, px = sx, py = sy; const MAX = Math.min((w + h) * 16, 40000)
  for (let iter = 0; iter < MAX; iter++) {
    const bDir = mooreDir(px, py, bx, by); if (bDir < 0) break; let qx = -1, qy = -1, newBx = bx, newBy = by
    for (let i = 0; i < 8; i++) { const d = (bDir + i) % 8, nx = px + MDX[d], ny = py + MDY[d]; if (nx < 0 || ny < 0 || nx >= w || ny >= h || !bin[ny * w + nx]) { if (nx >= 0 && ny >= 0 && nx < w && ny < h) { newBx = nx; newBy = ny } continue }; qx = nx; qy = ny; break }
    if (qx < 0) break; if (qx === sx && qy === sy && iter > 2) break; pts.push([qx, qy]); bx = newBx; by = newBy; px = qx; py = qy
  }
  return pts
}

function floodFillBg(local, lw, lh) { const reached = new Uint8Array(lw * lh); const stack = [0]; reached[0] = 1; while (stack.length) { const idx = stack.pop(), lx = idx % lw, ly = Math.floor(idx / lw); for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) { const nx = lx + dx, ny = ly + dy; if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue; const ni = ny * lw + nx; if (!reached[ni] && !local[ni]) { reached[ni] = 1; stack.push(ni) } } } return reached }

function findHoles(local, lw, lh, reached) {
  const visited = new Uint8Array(lw * lh); const holeContours = []
  for (let ly = 0; ly < lh; ly++) for (let lx = 0; lx < lw; lx++) {
    const idx = ly * lw + lx; if (local[idx] || reached[idx] || visited[idx]) continue
    const hStack = [idx]; visited[idx] = 1; const holePx = [[lx, ly]]
    while (hStack.length) { const hidx = hStack.pop(), hx = hidx % lw, hy = Math.floor(hidx / lw); for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) { const nx = hx + dx, ny = hy + dy; if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue; const ni = ny * lw + nx; if (!local[ni] && !reached[ni] && !visited[ni]) { visited[ni] = 1; hStack.push(ni); holePx.push([nx, ny]) } } }
    const invL = new Uint8Array(lw * lh); for (const [hx, hy] of holePx) invL[hy * lw + hx] = 1
    const hContour = mooreTrace(invL, lw, lh, lx, ly); if (hContour.length > 2) holeContours.push(hContour)
  }
  return holeContours
}

function simplify(pts, eps) {
  if (pts.length <= 2) return pts
  function dist(p, a, b) { const dx = b[0] - a[0], dy = b[1] - a[1], len2 = dx * dx + dy * dy; if (!len2) return Math.hypot(p[0] - a[0], p[1] - a[1]); const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2)); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy) }
  function rdp(pts) { if (pts.length <= 2) return pts; let md = 0, mi = 0; for (let i = 1; i < pts.length - 1; i++) { const d = dist(pts[i], pts[0], pts[pts.length - 1]); if (d > md) { md = d; mi = i } }; if (md > eps) { const l = rdp(pts.slice(0, mi + 1)), r = rdp(pts.slice(mi)); return [...l.slice(0, -1), ...r] }; return [pts[0], pts[pts.length - 1]] }
  return rdp([...pts, pts[0]]).slice(0, -1)
}

function polyToBezierPath(pts, tension = 0.4) {
  if (pts.length < 2) return ''; const n = pts.length
  let path = `M${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`
  for (let i = 0; i < n; i++) { const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n]; path += ` C${(p1[0] + (p2[0] - p0[0]) * tension / 3).toFixed(2)},${(p1[1] + (p2[1] - p0[1]) * tension / 3).toFixed(2)} ${(p2[0] - (p3[0] - p1[0]) * tension / 3).toFixed(2)},${(p2[1] - (p3[1] - p1[1]) * tension / 3).toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}` }
  return path + ' Z'
}

function glyphToVectorPath(binary, bounds, fw, epsilon) {
  const { x, y, w, h } = bounds; const pad = 2, lw = w + 2 * pad, lh = h + 2 * pad; const local = new Uint8Array(lw * lh)
  for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) local[(dy + pad) * lw + (dx + pad)] = binary[(y + dy) * fw + (x + dx)]
  let sx = -1, sy = -1; for (let ly = 0; ly < lh && sx < 0; ly++) for (let lx = 0; lx < lw; lx++) if (local[ly * lw + lx]) { sx = lx; sy = ly; break }
  if (sx < 0) return null
  const outerPts = mooreTrace(local, lw, lh, sx, sy); if (outerPts.length < 3) return null
  const normO = simplify(outerPts, epsilon).map(([cx, cy]) => [cx - pad, cy - pad]); let path = polyToBezierPath(normO)
  const reached = floodFillBg(local, lw, lh)
  for (const hContour of findHoles(local, lw, lh, reached)) { const simpH = simplify(hContour, epsilon); if (simpH.length < 3) continue; path += ' ' + polyToBezierPath(simpH.map(([cx, cy]) => [cx - pad, cy - pad])) }
  return path
}

function svgToOTPath(OT, svgData, scale, ascender) {
  const path = new OT.Path(); const tx = v => +v * scale; const ty = v => ascender - +v * scale
  const toks = svgData.match(/[MCLZmclz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/gi) || []; let i = 0, cmd = 'M'
  while (i < toks.length) { const tok = toks[i]; if (/^[MCLZmclz]$/.test(tok)) { cmd = tok.toUpperCase(); i++; continue }; if (cmd === 'M') { path.moveTo(tx(toks[i]), ty(toks[i + 1])); i += 2 } else if (cmd === 'L') { path.lineTo(tx(toks[i]), ty(toks[i + 1])); i += 2 } else if (cmd === 'C') { path.bezierCurveTo(tx(toks[i]), ty(toks[i + 1]), tx(toks[i + 2]), ty(toks[i + 3]), tx(toks[i + 4]), ty(toks[i + 5])); i += 6 } else if (cmd === 'Z') { path.close(); i++ } else i++ }
  return path
}

async function deflateBytes(data) {
  const ds = new CompressionStream('deflate-raw'); const writer = ds.writable.getWriter()
  writer.write(data instanceof Uint8Array ? data : new Uint8Array(data)); writer.close()
  const reader = ds.readable.getReader(); const chunks = []; while (true) { const { value, done } = await reader.read(); if (done) break; chunks.push(value) }
  const result = new Uint8Array(chunks.reduce((s, c) => s + c.length, 0)); let off = 0; for (const c of chunks) { result.set(c, off); off += c.length }; return result
}

async function sfntToWoff(sfntBuf) {
  const dv = new DataView(sfntBuf); const flavor = dv.getUint32(0); const numTables = dv.getUint16(4)
  const tables = []; for (let i = 0; i < numTables; i++) { const o = 12 + i * 16; tables.push({ tag: dv.getUint32(o), checksum: dv.getUint32(o + 4), offset: dv.getUint32(o + 8), length: dv.getUint32(o + 12) }) }
  const compressed = []; for (const t of tables) { const raw = new Uint8Array(sfntBuf, t.offset, t.length); try { const c = await deflateBytes(raw); compressed.push(c.length < t.length ? c : raw) } catch { compressed.push(raw) } }
  const pad4 = n => (4 - (n % 4)) % 4; let dataStart = 44 + numTables * 20; dataStart += pad4(dataStart)
  let totalLen = dataStart; const offsets = []; for (const c of compressed) { offsets.push(totalLen); totalLen += c.length; totalLen += pad4(c.length) }
  let totalSfnt = 12 + numTables * 16; for (const t of tables) { totalSfnt += t.length + pad4(t.length) }
  const woff = new ArrayBuffer(totalLen); const wv = new DataView(woff); const wu = new Uint8Array(woff)
  wv.setUint32(0, 0x774F4646); wv.setUint32(4, flavor); wv.setUint32(8, totalLen); wv.setUint16(12, numTables); wv.setUint16(14, 0); wv.setUint32(16, totalSfnt); wv.setUint16(20, 1); wv.setUint16(22, 0)
  for (let o = 24; o <= 40; o += 4) wv.setUint32(o, 0)
  for (let i = 0; i < numTables; i++) { const d = 44 + i * 20; wv.setUint32(d, tables[i].tag); wv.setUint32(d + 4, offsets[i]); wv.setUint32(d + 8, compressed[i].length); wv.setUint32(d + 12, tables[i].length); wv.setUint32(d + 16, tables[i].checksum) }
  for (let i = 0; i < numTables; i++) wu.set(compressed[i], offsets[i])
  return woff
}

export { toGray, otsu, gaussianBlur, dilate, labelComps, mergeFragments, groupRows, autoClassify, mooreDir, mooreTrace, floodFillBg, findHoles, simplify, polyToBezierPath, glyphToVectorPath, svgToOTPath, deflateBytes, sfntToWoff };
