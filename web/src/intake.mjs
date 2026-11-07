/**
 * intake.mjs: how anything gets onto the board, from a dropped file or a Figma link.
 *
 * the panel's "new node" flow has two doors, and both end in the same place: bytes with a digest,
 * and an element kind python's `Scene.add` accepts. everything that can go wrong on the way is
 * decided here, as pure functions, so it can be tested with no DOM and no network:
 *
 *   - what a file is, from its bytes and not its name (a .png that is really a zip is a zip)
 *   - what element it becomes, or why it cannot
 *   - what a Figma link points at, and the one conversion that quietly fetches nothing if wrong
 *   - what a Figma import costs against the account's request budget, before spending any of it
 *
 * the actual fetch and the actual file reader are injected, so nothing here touches the network.
 * credentials never pass through this file: it receives a function that already holds them.
 */

export class IntakeRefused extends Error {}

// what a board holds, copied from python's KIND_DTYPE so a test can pin the two together.
export const ELEMENT_KINDS = Object.freeze({
  frame: "image", sketch: "image", image: "image", video: "video", text: "text", model: "mesh",
});

// 25 MB: the biggest single file taken in the browser. a scan bigger than this should be resized
// first, and the refusal says so instead of letting a tab run out of memory partway through.
export const MAX_BYTES = 25 * 1024 * 1024;

/** sniff the real type from the first bytes. returns null for anything not recognised. */
export function sniff(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const is = (...sig) => sig.every((v, i) => b[i] === v);
  if (is(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)) return "png";
  if (is(0xff, 0xd8, 0xff)) return "jpeg";
  if (is(0x47, 0x49, 0x46, 0x38)) return "gif";
  if (is(0x52, 0x49, 0x46, 0x46) && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return "webp";
  if (is(0x50, 0x4b, 0x03, 0x04) || is(0x50, 0x4b, 0x05, 0x06)) return "zip";
  if (is(0x67, 0x6c, 0x54, 0x46)) return "glb";
  if (is(0x25, 0x50, 0x44, 0x46)) return "pdf";
  if (b.length > 12 && b[4] === 0x66 && b[5] === 0x74 && b[6] === 0x79 && b[7] === 0x70) {
    const brand = String.fromCharCode(b[8], b[9], b[10], b[11]);
    if (brand === "avif" || brand === "avis") return "avif";
    return "mp4"; // isom, mp41, mp42, qt  (mov shares the box layout)
  }
  if (is(0x1a, 0x45, 0xdf, 0xa3)) return "webm";
  const head = new TextDecoder("utf-8", { fatal: false }).decode(b.slice(0, 512)).trimStart().toLowerCase();
  if (head.startsWith("<svg") || (head.startsWith("<?xml") && head.includes("<svg"))) return "svg";
  return null;
}

// what each sniffed type becomes. `kind` is the element, `via` is how it needs handling first.
const TYPES = Object.freeze({
  png:  { kind: "image", via: "direct" },
  jpeg: { kind: "image", via: "direct" },
  webp: { kind: "image", via: "direct" },
  gif:  { kind: "image", via: "first-frame", note: "an animated gif is taken as its first frame" },
  avif: { kind: "image", via: "decode" },
  svg:  { kind: "image", via: "rasterise", note: "svg is drawn to pixels, since a sheet has to be read as pixels" },
  mp4:  { kind: "video", via: "direct" },
  webm: { kind: "video", via: "direct" },
  glb:  { kind: "model", via: "direct" },
  zip:  { kind: null, via: "unpack", note: "a zip is opened and each image inside is taken" },
  pdf:  { kind: null, via: "refuse", note: "pdf pages are not read here. export the page as png and drop that" },
});

/**
 * decide what a dropped file is. never trusts the name: a wrong extension is a warning, and the
 * bytes win. returns what to do with it, or throws with the reason.
 */
// refusal messages say what is wrong and not whose it is: the caller already shows the name beside
// them, and a name said twice reads as a stutter.
export function classify({ name = "", bytes, size = bytes?.length ?? 0 }) {
  if (!size) throw new IntakeRefused("it is empty");
  if (size > MAX_BYTES) {
    throw new IntakeRefused(`it is ${(size / 1048576).toFixed(1)} MB and the limit is ${MAX_BYTES / 1048576} MB. resize the scan and drop it again`);
  }
  const type = sniff(bytes);
  if (!type) {
    throw new IntakeRefused("not a type flowby reads (png, jpeg, webp, gif, avif, svg, mp4, webm, glb, zip)");
  }
  const spec = TYPES[type];
  if (spec.via === "refuse") throw new IntakeRefused(spec.note);
  const ext = (name.split(".").pop() || "").toLowerCase().replace("jpg", "jpeg");
  const mismatch = ext && ext !== type && !(type === "mp4" && ext === "mov") && ext !== name.toLowerCase();
  return {
    type, kind: spec.kind, via: spec.via, note: spec.note || null,
    warning: mismatch ? `${name} says .${ext} but its bytes are ${type}, so it is treated as ${type}` : null,
  };
}

/** the digest flowby names an asset by. injected crypto, so it runs in a browser, a worker or node. */
export async function digest(bytes, subtle = globalThis.crypto?.subtle) {
  if (!subtle) throw new IntakeRefused("no crypto available to hash this file with");
  const buf = await subtle.digest("SHA-256", bytes);
  return "sha256:" + [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** a dropped file as the element the board will hold. */
export async function toElement({ name, bytes }, { subtle } = {}) {
  const plan = classify({ name, bytes });
  if (plan.via === "unpack") {
    throw new IntakeRefused(`${name} is a zip: open it first with unpackZip(), then take each image`);
  }
  return {
    kind: plan.kind === "image" ? "image" : plan.kind,
    label: name.replace(/\.[^.]+$/, ""),
    asset: await digest(bytes, subtle),
    bytes: bytes.length, sniffed: plan.type, via: plan.via,
    warning: plan.warning, source: { from: "upload", name },
  };
}

// --- zips ------------------------------------------------------------------------------------

export const ZIP_LIMITS = Object.freeze({ entries: 200, total: 100 * 1024 * 1024, ratio: 100 });

/**
 * open a zip safely. `unzip` is injected (fflate's unzipSync in the browser) so this stays pure.
 * a zip is untrusted input with one famous attack: a few kilobytes that expand to gigabytes. so
 * the size of every entry is checked from the archive's own directory BEFORE anything is inflated,
 * and the whole thing is refused if it claims more than the limits, rather than opening it and
 * hoping. paths that climb out of the archive, hidden files and folders are skipped by name.
 */
export function unpackZip(bytes, unzip, limits = ZIP_LIMITS) {
  const listing = [];
  const gathered = unzip(bytes, {
    filter: (entry) => {
      listing.push({ name: entry.name, size: entry.originalSize, packed: entry.size });
      return false; // inspect first, inflate nothing
    },
  });
  void gathered;
  if (listing.length > limits.entries) {
    throw new IntakeRefused(`the zip holds ${listing.length} entries and the limit is ${limits.entries}`);
  }
  const claimed = listing.reduce((n, e) => n + e.size, 0);
  if (claimed > limits.total) {
    throw new IntakeRefused(`the zip would expand to ${(claimed / 1048576).toFixed(0)} MB and the limit is ${limits.total / 1048576} MB`);
  }
  const packed = listing.reduce((n, e) => n + e.packed, 0) || 1;
  if (claimed / packed > limits.ratio) {
    throw new IntakeRefused(`the zip expands ${(claimed / packed).toFixed(0)} times its size, which is how a zip bomb looks`);
  }
  const skipped = [], wanted = [];
  for (const e of listing) {
    const base = e.name.split("/").pop();
    if (e.name.endsWith("/")) continue;                                   // a folder
    if (e.name.split("/").includes("..") || e.name.startsWith("/")) { skipped.push({ name: e.name, reason: "its path climbs out of the archive" }); continue; }
    if (e.name.startsWith("__MACOSX/") || base.startsWith(".")) { skipped.push({ name: e.name, reason: "hidden or system file" }); continue; }
    if (e.size > MAX_BYTES) { skipped.push({ name: e.name, reason: `${(e.size / 1048576).toFixed(1)} MB is over the ${MAX_BYTES / 1048576} MB file limit` }); continue; }
    wanted.push(e.name);
  }
  const opened = unzip(bytes, { filter: (entry) => wanted.includes(entry.name) });
  const files = Object.entries(opened).map(([name, data]) => ({ name: name.split("/").pop(), bytes: data }));
  return { files, skipped };
}

// --- figma -----------------------------------------------------------------------------------

const FIGMA_TYPES = ["file", "design", "board", "proto", "make", "slides"];

/**
 * read a figma link. the file key and the node id come out of the url, and the node id needs one
 * conversion: the url writes 1-2 and the rest api wants 1:2. fetching with the wrong form returns
 * a quiet null for that node, not an error, which is why this is a tested function.
 */
export function parseFigma(link) {
  let url;
  try { url = new URL(String(link).trim()); } catch { throw new IntakeRefused("that is not a link"); }
  if (!/(^|\.)figma\.com$/.test(url.hostname)) throw new IntakeRefused(`${url.hostname} is not figma.com`);
  const parts = url.pathname.split("/").filter(Boolean);
  const type = parts[0];
  if (!FIGMA_TYPES.includes(type)) throw new IntakeRefused(`a figma link starts /design/ or /file/, not /${type ?? ""}`);
  const key = parts[1];
  if (!key || !/^[A-Za-z0-9]{10,40}$/.test(key)) throw new IntakeRefused("that link has no file key in it");
  let branch = null, fileKey = key;
  if (parts[2] === "branch" && parts[3]) { branch = parts[3]; fileKey = parts[3]; }
  const raw = url.searchParams.get("node-id");
  const nodeId = raw ? raw.replace(/-/g, ":") : null;
  if (nodeId && !/^\d+:\d+(;\d+:\d+)*$/.test(nodeId)) throw new IntakeRefused(`node id ${raw} is not one figma uses`);
  return { fileKey, branch, nodeId, type, name: decodeURIComponent(parts[branch ? 4 : 2] ?? "") || null };
}

/**
 * what an import costs, before any of it is spent. figma's tier 1 endpoints (file, nodes, image)
 * allow 20 requests a MONTH on a view or collab seat, and 10 to 20 a minute on dev or full. an
 * import of N frames is one nodes call plus ceil(N / batch) image calls, so it is cheap if batched
 * and ruinous if each frame is fetched alone.
 */
export const FIGMA_LIMITS = Object.freeze({
  view: { per: "month", amount: 20 },
  collab: { per: "month", amount: 20 },
  dev: { per: "minute", amount: 15 },
  full: { per: "minute", amount: 15 },
});
export const IMAGE_BATCH = 50; // node ids per images call; a long query string is the real ceiling

export function importCost(frames, { seat = "view", batch = IMAGE_BATCH } = {}) {
  if (!(frames >= 1)) throw new IntakeRefused("there are no frames to import");
  const limit = FIGMA_LIMITS[seat];
  if (!limit) throw new IntakeRefused(`${seat} is not a figma seat (view, collab, dev, full)`);
  const requests = 1 + Math.ceil(frames / batch);       // one nodes call, then batched image calls
  const naive = 1 + frames;                             // what fetching each frame alone would cost
  const monthly = limit.per === "month";
  // a monthly cap is a ceiling: spend past it and there is nothing until next month. a per-minute
  // limit is a rate: 31 requests against 15 a minute is not refused, it is paced over 3 minutes.
  const minutes = monthly ? 0 : Math.ceil(requests / limit.amount);
  return {
    requests, naive, limit, seat, minutes,
    fits: monthly ? requests <= limit.amount : true,
    note: monthly
      ? `${requests} of this month's ${limit.amount} requests. a ${seat} seat has no more until next month`
      : minutes <= 1
        ? `${requests} requests, against ${limit.amount} a minute`
        : `${requests} requests at ${limit.amount} a minute, so about ${minutes} minutes`,
  };
}

/** refuse before fetching if the import would not fit, naming what it would use. */
export function planImport(frames, options) {
  const cost = importCost(frames, options);
  if (!cost.fits) {
    throw new IntakeRefused(
      `importing ${frames} frames needs ${cost.requests} requests and ${cost.seat} seats get ${cost.limit.amount} a ${cost.limit.per}. ` +
      `pick fewer frames, or use a dev or full seat`,
    );
  }
  return cost;
}

/**
 * pull frames out of a nodes response. the nodes map may hold null for an id that does not exist
 * in the file, and an image map may hold null for a node that has nothing to render, so both are
 * reported by id and never silently skipped.
 */
export function framesOf(nodesResponse, wanted = null) {
  const nodes = nodesResponse?.nodes;
  if (!nodes) throw new IntakeRefused("figma returned no nodes map");
  const frames = [], missing = [];
  for (const [id, entry] of Object.entries(nodes)) {
    if (!entry || !entry.document) { missing.push(id); continue; }
    collect(entry.document, frames);
  }
  if (wanted) for (const id of wanted) if (!(id in nodes)) missing.push(id);
  return { frames, missing: [...new Set(missing)] };
}

/**
 * walk a figma tree and list what can be imported as an image.
 *
 * a FRAME, COMPONENT or COMPONENT_SET is importable and its children are part of it, so they are not
 * listed again. a SECTION is only a container with no pixels of its own: importing "Moodboard" as
 * one picture and its two frames as two more would file the same content twice. so a section is
 * walked, never listed, and its frames carry `section` so the picker can group them.
 */
function collect(node, out, section = null) {
  if (!node) return;
  if (node.type === "FRAME" || node.type === "COMPONENT" || node.type === "COMPONENT_SET") {
    const box = node.absoluteBoundingBox || {};
    out.push({
      id: node.id, name: node.name || node.id, type: node.type,
      width: box.width ?? null, height: box.height ?? null, section,
    });
    return; // everything inside belongs to this frame
  }
  if (node.type === "CANVAS" || node.type === "DOCUMENT" || node.type === "SECTION") {
    const inside = node.type === "SECTION" ? (node.name || node.id) : section;
    for (const child of node.children || []) collect(child, out, inside);
  }
}

/**
 * choose a scale that keeps a frame under figma's 32 megapixel cap, so figma does not quietly
 * scale it down by an amount nobody chose. returns the scale and whether it had to be reduced.
 */
export function exportScale(frame, { want = 2, cap = 32e6 } = {}) {
  const { width, height } = frame;
  if (!width || !height) return { scale: Math.min(want, 4), reduced: false, known: false };
  const limit = Math.sqrt(cap / (width * height));
  const scale = Math.max(0.01, Math.min(want, 4, Math.floor(limit * 100) / 100));
  return { scale, reduced: scale < Math.min(want, 4), known: true, pixels: Math.round(width * scale * height * scale) };
}

/**
 * read an images response into per-frame results. a null url is a frame that did not render, and it
 * is listed with the reason figma gives for it, so an import of 12 frames never quietly becomes 11.
 */
export function imageUrls(imagesResponse, ids) {
  if (imagesResponse?.err) throw new IntakeRefused(`figma refused the export: ${imagesResponse.err}`);
  const map = imagesResponse?.images;
  if (!map) throw new IntakeRefused("figma returned no images map");
  const ok = [], failed = [];
  for (const id of ids) {
    if (map[id]) ok.push({ id, url: map[id] });
    else failed.push({ id, reason: id in map ? "figma could not render it (hidden, zero opacity, or empty)" : "figma did not return it" });
  }
  return { ok, failed };
}

/**
 * copy the exported bytes into flowby's own store NOW. figma's image urls expire after 30 days, so
 * storing the url instead of the bytes makes an import that quietly dies next month. `fetchBytes`
 * is injected and must return a Uint8Array. every frame becomes an element with a digest.
 */
export async function importFrames({ frames, urls, fetchBytes, file, subtle }) {
  const byId = new Map(frames.map((f) => [f.id, f]));
  const elements = [], failed = [...urls.failed];
  for (const { id, url } of urls.ok) {
    let bytes;
    try { bytes = await fetchBytes(url); } catch (e) { failed.push({ id, reason: `download failed: ${e.message}` }); continue; }
    const type = sniff(bytes);
    if (type !== "png" && type !== "jpeg" && type !== "svg") {
      failed.push({ id, reason: `figma sent ${type ?? "unrecognised bytes"} instead of an image` }); continue;
    }
    const frame = byId.get(id);
    elements.push({
      kind: "frame", label: frame?.name ?? id, asset: await digest(bytes, subtle), bytes: bytes.length,
      sniffed: type, via: "direct", warning: null,
      source: { from: "figma", fileKey: file.fileKey, nodeId: id, name: frame?.name ?? null, copied: true },
    });
  }
  return { elements, failed };
}
