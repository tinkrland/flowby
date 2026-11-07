/**
 * intake.test.mjs: how a file or a figma link becomes something the board can hold.
 *
 * the files in tests/fixtures/files were made by real encoders (pillow for the images including
 * avif, ffmpeg for mp4 and webm), so `sniff` is held to bytes it did not write. the figma
 * responses follow the shapes in figma's rest docs, nulls included, because the nulls are where
 * an import quietly loses a frame. nothing here touches the network.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import * as intake from "../src/intake.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const file = (n) => new Uint8Array(fs.readFileSync(path.join(here, "fixtures", "files", n)));
const json = (n) => JSON.parse(fs.readFileSync(path.join(here, "fixtures", n), "utf8"));

// --- what a file is -------------------------------------------------------------------------

test("every real file type is recognised from its bytes", () => {
  const expect = {
    "a.png": "png", "a.jpg": "jpeg", "a.webp": "webp", "a.gif": "gif", "a.avif": "avif",
    "a.svg": "svg", "a_xml.svg": "svg", "a.mp4": "mp4", "a.webm": "webm", "a.glb": "glb",
    "a.zip": "zip", "a.pdf": "pdf",
  };
  for (const [name, type] of Object.entries(expect)) assert.equal(intake.sniff(file(name)), type, name);
});

test("plain text and empty bytes are not any type", () => {
  assert.equal(intake.sniff(file("text.png")), null);
  assert.equal(intake.sniff(new Uint8Array(0)), null);
});

test("the bytes win over the name: a jpeg called .png is a jpeg, with a warning", () => {
  const r = intake.classify({ name: "fake.png", bytes: file("fake.png") });
  assert.equal(r.type, "jpeg");
  assert.match(r.warning, /says \.png but its bytes are jpeg/);
});

test("a file whose name and bytes agree has no warning", () => {
  assert.equal(intake.classify({ name: "a.png", bytes: file("a.png") }).warning, null);
  assert.equal(intake.classify({ name: "a.jpg", bytes: file("a.jpg") }).warning, null); // jpg is jpeg
});

test("an mp4 named .mov is not flagged, since they share a container", () => {
  assert.equal(intake.classify({ name: "clip.mov", bytes: file("a.mp4") }).warning, null);
});

test("each type becomes the element kind the board holds", () => {
  const kind = (n) => intake.classify({ name: n, bytes: file(n) }).kind;
  assert.equal(kind("a.png"), "image");
  assert.equal(kind("a.svg"), "image");
  assert.equal(kind("a.mp4"), "video");
  assert.equal(kind("a.glb"), "model");
});

test("the element kinds intake knows are exactly the ones python's Scene.add accepts", () => {
  const python = fs.readFileSync(path.join(here, "..", "..", "src", "flowby", "scene.py"), "utf8");
  const block = python.match(/KIND_DTYPE\s*=\s*\{([^}]+)\}/)[1];
  const kinds = [...block.matchAll(/"([a-z]+)":/g)].map((m) => m[1]);
  assert.deepEqual([...kinds].sort(), Object.keys(intake.ELEMENT_KINDS).sort());
  for (const name of ["a.png", "a.mp4", "a.glb"]) {
    assert.ok(kinds.includes(intake.classify({ name, bytes: file(name) }).kind), name);
  }
});

test("a pdf is refused with what to do instead", () => {
  assert.throws(() => intake.classify({ name: "a.pdf", bytes: file("a.pdf") }), (e) => /^pdf pages are not read here\. export the page as png/.test(e.message));
});

test("a zip is routed to unpacking and not taken as an image", () => {
  const r = intake.classify({ name: "a.zip", bytes: file("a.zip") });
  assert.equal(r.via, "unpack");
  assert.equal(r.kind, null);
});

test("an empty file, an unknown file and an oversize file each refuse with their own reason", () => {
  assert.throws(() => intake.classify({ name: "empty.png", bytes: file("empty.png") }), (e) => e.message === "it is empty");
  assert.throws(() => intake.classify({ name: "text.png", bytes: file("text.png") }), (e) => e.message.startsWith("not a type flowby reads"));
  assert.throws(
    () => intake.classify({ name: "huge.png", bytes: file("a.png"), size: 40 * 1048576 }),
    (e) => e.message.startsWith("it is 40.0 MB and the limit is 25 MB"),
  );
});

test("an upload becomes an element with a real sha256 and the name as its label", async () => {
  const el = await intake.toElement({ name: "sketch one.png", bytes: file("a.png") });
  assert.equal(el.kind, "image");
  assert.equal(el.label, "sketch one");
  assert.match(el.asset, /^sha256:[0-9a-f]{64}$/);
  assert.deepEqual(el.source, { from: "upload", name: "sketch one.png" });
});

test("the digest matches an independent sha256 of the same bytes", async () => {
  const bytes = file("a.png");
  assert.equal(await intake.digest(bytes), "sha256:" + createHash("sha256").update(bytes).digest("hex"));
});

test("the same bytes give the same asset, so a re-dropped file is not a new asset", async () => {
  const a = await intake.toElement({ name: "x.png", bytes: file("a.png") });
  const b = await intake.toElement({ name: "y.png", bytes: file("a.png") });
  assert.equal(a.asset, b.asset);
});

test("a zip handed straight to toElement is refused, naming the step it needs first", async () => {
  await assert.rejects(intake.toElement({ name: "a.zip", bytes: file("a.zip") }), /open it first with unpackZip/);
});

// --- figma links ----------------------------------------------------------------------------

test("a design link gives the file key and the node id in the form the api wants", () => {
  const r = intake.parseFigma("https://www.figma.com/design/AbC123xyz789QWERTY/Brand-sheets?node-id=1-2&t=zz");
  assert.equal(r.fileKey, "AbC123xyz789QWERTY");
  assert.equal(r.nodeId, "1:2"); // the url writes 1-2, the rest api wants 1:2
  assert.equal(r.name, "Brand-sheets");
});

test("the older /file/ form works the same", () => {
  assert.equal(intake.parseFigma("https://www.figma.com/file/AbC123xyz789QWERTY/Old?node-id=10-20").nodeId, "10:20");
});

test("a link with no node id selects the whole file", () => {
  assert.equal(intake.parseFigma("https://www.figma.com/design/AbC123xyz789QWERTY/Name").nodeId, null);
});

test("a branch link uses the branch key, because that is the one the api wants", () => {
  const r = intake.parseFigma("https://www.figma.com/design/AbC123xyz789QWERTY/branch/BrAnCh9876543210/Name?node-id=3-4");
  assert.equal(r.fileKey, "BrAnCh9876543210");
  assert.equal(r.branch, "BrAnCh9876543210");
});

test("a nested instance id (with semicolons) survives the conversion", () => {
  assert.equal(intake.parseFigma("https://www.figma.com/design/AbC123xyz789QWERTY/N?node-id=1-2;3-4").nodeId, "1:2;3:4");
});

test("things that are not figma links are refused with the reason", () => {
  assert.throws(() => intake.parseFigma("not a url"), /not a link/);
  assert.throws(() => intake.parseFigma("https://example.com/design/AbC123xyz789QWERTY/x"), /not figma\.com/);
  assert.throws(() => intake.parseFigma("https://www.figma.com/community/plugin/123"), /starts \/design\/ or \/file\//);
  assert.throws(() => intake.parseFigma("https://www.figma.com/design/short/x"), /no file key/);
  assert.throws(() => intake.parseFigma("https://www.figma.com/design/AbC123xyz789QWERTY/x?node-id=abc"), /not one figma uses/);
});

test("a lookalike host is not figma", () => {
  assert.throws(() => intake.parseFigma("https://notfigma.com/design/AbC123xyz789QWERTY/x"), /not figma\.com/);
  assert.throws(() => intake.parseFigma("https://figma.com.evil.io/design/AbC123xyz789QWERTY/x"), /not figma\.com/);
});

// --- the request budget ---------------------------------------------------------------------

test("a batched import costs one nodes call plus one image call per fifty frames", () => {
  assert.equal(intake.importCost(1).requests, 2);
  assert.equal(intake.importCost(50).requests, 2);
  assert.equal(intake.importCost(51).requests, 3);
  assert.equal(intake.importCost(120).requests, 4);
});

test("fetching frames one at a time would cost far more, and the cost reports both", () => {
  const c = intake.importCost(30);
  assert.equal(c.requests, 2);
  assert.equal(c.naive, 31);
});

test("a view seat has 20 requests a month and says so in plain words", () => {
  const c = intake.importCost(10, { seat: "view" });
  assert.deepEqual(c.limit, { per: "month", amount: 20 });
  assert.match(c.note, /2 of this month's 20 requests/);
  assert.match(c.note, /no more until next month/);
});

test("a dev seat is limited per minute and the note says that instead", () => {
  const c = intake.importCost(10, { seat: "dev" });
  assert.equal(c.limit.per, "minute");
  assert.doesNotMatch(c.note, /month/);
});

test("planImport refuses an import a seat cannot afford, before fetching anything", () => {
  assert.throws(() => intake.planImport(1500, { seat: "view" }), /needs 31 requests and view seats get 20 a month/);
  assert.doesNotThrow(() => intake.planImport(1500, { seat: "dev" }));
});

test("a per-minute limit is a rate, so a big import is paced and not refused", () => {
  const c = intake.importCost(1500, { seat: "dev" });
  assert.equal(c.requests, 31);
  assert.equal(c.fits, true);
  assert.equal(c.minutes, 3);                      // 31 requests at 15 a minute
  assert.match(c.note, /31 requests at 15 a minute, so about 3 minutes/);
  assert.equal(intake.importCost(10, { seat: "dev" }).minutes, 1);
});

test("a monthly limit is a ceiling and has no pacing", () => {
  const c = intake.importCost(10, { seat: "collab" });
  assert.equal(c.minutes, 0);
  assert.equal(c.fits, true);
  assert.equal(intake.importCost(1500, { seat: "collab" }).fits, false);
});

test("zero frames and unknown seats are refused", () => {
  assert.throws(() => intake.importCost(0), /no frames/);
  assert.throws(() => intake.importCost(5, { seat: "guest" }), /not a figma seat/);
});

// --- reading figma's responses --------------------------------------------------------------

test("frames are found on the page and inside sections, and a frame's children are not duplicated", () => {
  const { frames } = intake.framesOf(json("figma_nodes.json"));
  assert.deepEqual(frames.map((f) => f.id), ["1:2", "1:3", "1:4", "2:2", "2:3"]);
  assert.ok(!frames.some((f) => f.id === "1:9"), "a nested frame is part of its parent");
  assert.ok(!frames.some((f) => f.id === "1:5"), "a text layer is not a frame");
});

test("a section is walked and never listed, so its content is not imported twice", () => {
  const { frames } = intake.framesOf(json("figma_nodes.json"));
  assert.ok(!frames.some((f) => f.type === "SECTION"));
  const inside = frames.filter((f) => f.section === "Moodboard");
  assert.deepEqual(inside.map((f) => f.id), ["2:2", "2:3"]);
  assert.equal(frames.find((f) => f.id === "1:2").section, null);
});

test("a null entry in the nodes map is reported as missing and not silently dropped", () => {
  assert.deepEqual(intake.framesOf(json("figma_nodes.json")).missing, ["9:9"]);
});

test("an id that was asked for and never came back is reported as missing too", () => {
  assert.ok(intake.framesOf(json("figma_nodes.json"), ["1:2", "7:7"]).missing.includes("7:7"));
});

test("a response with no nodes map is refused", () => {
  assert.throws(() => intake.framesOf({}), /no nodes map/);
});

test("a frame keeps its size, so the export scale can be chosen from it", () => {
  const f = intake.framesOf(json("figma_nodes.json")).frames.find((x) => x.id === "1:3");
  assert.deepEqual([f.width, f.height], [2000, 640]);
});

test("image urls split into those that rendered and those that did not, with a reason each", () => {
  const { ok, failed } = intake.imageUrls(json("figma_images.json"), ["1:2", "1:3", "1:4", "2:2", "5:5"]);
  assert.deepEqual(ok.map((x) => x.id), ["1:2", "1:3", "2:2"]);
  assert.deepEqual(failed.map((x) => x.id), ["1:4", "5:5"]);
  assert.match(failed[0].reason, /hidden, zero opacity, or empty/);
  assert.match(failed[1].reason, /did not return it/);
});

test("an images response carrying an error is refused with figma's words", () => {
  assert.throws(() => intake.imageUrls({ err: "Render timeout", images: null }, ["1:2"]), /figma refused the export: Render timeout/);
});

test("the export scale stays under figma's 32 megapixel cap instead of letting figma shrink it silently", () => {
  const big = intake.exportScale({ width: 6000, height: 4000 }, { want: 2 }); // 24 MP at 1x, 96 MP at 2x
  assert.equal(big.reduced, true);
  assert.ok(big.pixels <= 32e6, `${big.pixels} is over the cap`);
  const small = intake.exportScale({ width: 800, height: 600 }, { want: 2 });
  assert.deepEqual([small.scale, small.reduced], [2, false]);
});

test("the export scale never exceeds 4, which is figma's own ceiling", () => {
  assert.equal(intake.exportScale({ width: 10, height: 10 }, { want: 9 }).scale, 4);
});

test("a frame with an unknown size falls back to the wanted scale and says the size was unknown", () => {
  const r = intake.exportScale({ width: null, height: null }, { want: 2 });
  assert.deepEqual([r.scale, r.known], [2, false]);
});

// --- copying the bytes in -------------------------------------------------------------------

const frames = () => intake.framesOf(json("figma_nodes.json")).frames;

test("an import copies the bytes and files each frame as an element with a digest, not a link", async () => {
  const urls = intake.imageUrls(json("figma_images.json"), ["1:2", "1:3"]);
  const seen = [];
  const out = await intake.importFrames({
    frames: frames(), urls, file: { fileKey: "AbC123xyz789QWERTY" },
    fetchBytes: async (u) => { seen.push(u); return file("a.png"); },
  });
  assert.equal(seen.length, 2);
  assert.equal(out.elements.length, 2);
  for (const el of out.elements) {
    assert.equal(el.kind, "frame");
    assert.match(el.asset, /^sha256:[0-9a-f]{64}$/);
    assert.equal(el.source.copied, true);
    assert.equal(JSON.stringify(el).includes("figma.com/img"), false, "the expiring url must not be stored");
  }
  assert.deepEqual(out.elements.map((e) => e.label), ["Cover", "Alphabet sheet"]);
});

test("a frame that fails to download is listed as failed and the rest still import", async () => {
  const urls = intake.imageUrls(json("figma_images.json"), ["1:2", "1:3", "2:2"]);
  let n = 0;
  const out = await intake.importFrames({
    frames: frames(), urls, file: { fileKey: "k" },
    fetchBytes: async () => { if (++n === 2) throw new Error("403 expired"); return file("a.png"); },
  });
  assert.equal(out.elements.length, 2);
  assert.equal(out.failed.length, 1);
  assert.match(out.failed[0].reason, /download failed: 403 expired/);
});

test("figma sending something that is not an image is a failure for that frame, not a corrupt element", async () => {
  const urls = intake.imageUrls(json("figma_images.json"), ["1:2"]);
  const out = await intake.importFrames({ frames: frames(), urls, file: { fileKey: "k" }, fetchBytes: async () => file("text.png") });
  assert.equal(out.elements.length, 0);
  assert.match(out.failed[0].reason, /unrecognised bytes instead of an image/);
});

test("frames that figma could not render carry through into failed, so 4 requested is never quietly 3", async () => {
  const urls = intake.imageUrls(json("figma_images.json"), ["1:2", "1:3", "1:4", "2:2"]);
  const out = await intake.importFrames({ frames: frames(), urls, file: { fileKey: "k" }, fetchBytes: async () => file("a.png") });
  assert.equal(out.elements.length + out.failed.length, 4);
  assert.deepEqual(out.failed.map((f) => f.id), ["1:4"]);
});

test("no credential ever appears in what intake returns", async () => {
  const urls = intake.imageUrls(json("figma_images.json"), ["1:2"]);
  const out = await intake.importFrames({ frames: frames(), urls, file: { fileKey: "k" }, fetchBytes: async () => file("a.png") });
  assert.doesNotMatch(JSON.stringify(out), /X-Figma-Token|Bearer|figd_/i);
});

// --- zips -----------------------------------------------------------------------------------

import { unzipSync } from "fflate";

test("a zip opens to its images, skipping folders, hidden files and system files by name", () => {
  const { files, skipped } = intake.unpackZip(file("multi.zip"), unzipSync);
  assert.deepEqual(files.map((f) => f.name).sort(), ["notes.txt", "one.png", "two.jpg"]);
  const why = Object.fromEntries(skipped.map((s) => [s.name, s.reason]));
  assert.match(why["__MACOSX/sheets/._one.png"], /hidden or system/);
  assert.match(why["sheets/.DS_Store"], /hidden or system/);
});

test("files taken from a zip are classified by their bytes, so a text file inside is refused later", () => {
  const { files } = intake.unpackZip(file("multi.zip"), unzipSync);
  const kinds = files.map((f) => { try { return [f.name, intake.classify(f).type]; } catch { return [f.name, "refused"]; } });
  assert.deepEqual(Object.fromEntries(kinds), { "one.png": "png", "two.jpg": "jpeg", "notes.txt": "refused" });
});

test("an entry whose path climbs out of the archive is skipped and named, and the rest still open", () => {
  const { files, skipped } = intake.unpackZip(file("climb.zip"), unzipSync);
  assert.deepEqual(files.map((f) => f.name), ["ok.png"]);
  assert.match(skipped.find((s) => s.name.includes("escape")).reason, /climbs out of the archive/);
});

test("a zip bomb is refused from its directory, before anything is inflated", () => {
  const size = file("bomb.zip").length;
  assert.ok(size < 400 * 1024, `the bomb should be small on disk, was ${size}`);
  assert.throws(() => intake.unpackZip(file("bomb.zip"), unzipSync), /would expand to 200 MB and the limit is 100 MB/);
});

test("the ratio check names a bomb even when the total is under the size limit", () => {
  assert.throws(() => intake.unpackZip(file("bomb.zip"), unzipSync, { entries: 200, total: 500 * 1048576, ratio: 100 }), /which is how a zip bomb looks/);
});

test("too many entries is refused with the count", () => {
  assert.throws(() => intake.unpackZip(file("many.zip"), unzipSync), /holds 250 entries and the limit is 200/);
});

test("one oversize file inside is skipped by name and does not sink the others", async () => {
  // incompressible bytes, so this is a big honest file and not a bomb: the ratio check passes
  // and it is the per-file limit that has to catch it.
  // built here and not stored: 30 MB of random bytes does not belong in a git repo
  const { zipSync } = await import("fflate");
  const { randomBytes } = await import("node:crypto");
  const png = file("a.png");
  const big = new Uint8Array(png.length + 30 * 1048576);
  big.set(png); big.set(randomBytes(30 * 1048576), png.length);
  const archive = zipSync({ "huge.png": [big, { level: 1 }], "small.png": png });
  const { files, skipped } = intake.unpackZip(archive, unzipSync);
  assert.deepEqual(files.map((f) => f.name), ["small.png"]);
  assert.equal(skipped.length, 1);
  assert.equal(skipped[0].name, "huge.png");
  assert.match(skipped[0].reason, /30\.0 MB is over the 25 MB file limit/);
});

test("the bomb check inflates nothing: a listing-only pass reads sizes without producing bytes", () => {
  let inflated = 0;
  const spy = (bytes, opts) => {
    const out = unzipSync(bytes, { filter: (e) => { const keep = opts.filter(e); if (keep) inflated += e.originalSize; return keep; } });
    return out;
  };
  assert.throws(() => intake.unpackZip(file("bomb.zip"), spy));
  assert.equal(inflated, 0);
});

test("a refusal never repeats the file name, since the panel already shows it", () => {
  for (const [name, bytes] of [["x.pdf", file("a.pdf")], ["x.png", file("text.png")], ["x.png", file("empty.png")]]) {
    try { intake.classify({ name, bytes }); assert.fail("should have refused"); }
    catch (e) { assert.equal(e.message.includes(name), false, `${JSON.stringify(e.message)} repeats ${name}`); }
  }
});
