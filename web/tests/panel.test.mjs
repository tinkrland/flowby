/**
 * panel.test.mjs: the new-node panel, driven end to end from node with no DOM and no network.
 *
 * the figma token is the thing most worth proving. the tests below do not trust the comments in
 * panel.mjs: they put a recognisable token in, then look for it in everything the interface can
 * see, in every request the client would make to anyone but figma, and in the source itself.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as panel from "../src/panel.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const file = (n) => new Uint8Array(fs.readFileSync(path.join(here, "fixtures", "files", n)));
const json = (n) => JSON.parse(fs.readFileSync(path.join(here, "fixtures", n), "utf8"));
const TOKEN = "figd_SECRETSECRETSECRET_9f3a";

const run = (...actions) => actions.reduce((s, a) => panel.reduce(s, a), panel.initial());

// --- uploads ---------------------------------------------------------------------------------

test("dropped files are queued by what their bytes are, and bad ones are refused by name", () => {
  const s = run({ type: "files", files: [
    { name: "sheet.png", bytes: file("a.png") },
    { name: "clip.mp4", bytes: file("a.mp4") },
    { name: "notes.png", bytes: file("text.png") },
    { name: "empty.png", bytes: file("empty.png") },
    { name: "doc.pdf", bytes: file("a.pdf") },
  ] });
  assert.deepEqual(s.queue.map((q) => [q.name, q.kind]), [["sheet.png", "image"], ["clip.mp4", "video"]]);
  assert.deepEqual(s.refused.map((r) => r.name), ["notes.png", "empty.png", "doc.pdf"]);
  assert.match(s.refused[2].reason, /export the page as png/);
});

test("nothing dropped is silently lost: queued plus refused equals what was dropped", () => {
  const files = ["a.png", "a.jpg", "text.png", "a.glb", "empty.png", "a.zip"].map((n) => ({ name: n, bytes: file(n) }));
  const s = run({ type: "files", files });
  assert.equal(s.queue.length + s.refused.length, files.length);
});

test("a zip is queued as a zip, then replaced by the images inside it", () => {
  let s = run({ type: "files", files: [{ name: "pack.zip", bytes: file("a.zip") }] });
  assert.equal(s.queue[0].via, "unpack");
  assert.equal(panel.view(s).canPlace, false, "a zip alone cannot be placed");
  const id = s.queue[0].id;
  s = panel.reduce(s, { type: "unpacked", id, files: [{ name: "inner.png", bytes: file("a.png") }, { name: "inner.txt", bytes: file("text.png") }] });
  assert.deepEqual(s.queue.map((q) => q.name), ["inner.png"]);
  assert.equal(s.refused.length, 1);
  assert.equal(panel.view(s).canPlace, true);
});

test("a zip inside a zip is refused and not opened", () => {
  let s = run({ type: "files", files: [{ name: "pack.zip", bytes: file("a.zip") }] });
  s = panel.reduce(s, { type: "unpacked", id: s.queue[0].id, files: [{ name: "again.zip", bytes: file("a.zip") }] });
  assert.equal(s.queue.length, 0);
  assert.match(s.refused[0].reason, /zip inside a zip/);
});

test("the queue is capped, and the overflow is refused with the reason", () => {
  const files = Array.from({ length: 45 }, (_, i) => ({ name: `f${i}.png`, bytes: file("a.png") }));
  const s = run({ type: "files", files });
  assert.equal(s.queue.length, 40);
  assert.equal(s.refused.length, 5);
  assert.match(s.refused[0].reason, /queue holds 40/);
});

test("a queued file with a mismatched name carries its warning to the interface", () => {
  const s = run({ type: "files", files: [{ name: "fake.png", bytes: file("fake.png") }] });
  assert.match(panel.view(s).queue[0].warning, /bytes are jpeg/);
});

test("placing removes exactly the placed files from the queue and records the elements", () => {
  let s = run({ type: "files", files: [{ name: "a.png", bytes: file("a.png") }, { name: "b.png", bytes: file("a.jpg") }] });
  const [first] = s.queue;
  s = panel.reduce(s, { type: "placed", ids: [first.id], elements: [{ kind: "image", label: "a" }] });
  assert.deepEqual(s.queue.map((q) => q.name), ["b.png"]);
  assert.equal(s.placed.length, 1);
});

test("the view reports a size and never hands the raw bytes to the interface", () => {
  const s = run({ type: "files", files: [{ name: "a.png", bytes: file("a.png") }] });
  const q = panel.view(s).queue[0];
  assert.equal(q.size, 77);
  assert.equal("bytes" in q, false);
});

// --- the figma flow --------------------------------------------------------------------------

test("the figma door walks link, token, pick in order", () => {
  let s = run({ type: "open", door: "figma" });
  assert.equal(s.figma.step, "link");
  s = panel.reduce(s, { type: "figma-parsed", parsed: { fileKey: "k" } });
  assert.equal(s.figma.step, "token");
  const frames = intake_frames();
  s = panel.reduce(s, { type: "figma-frames", frames: frames.frames, missing: frames.missing });
  assert.equal(s.figma.step, "pick");
  assert.deepEqual(s.figma.missing, ["9:9"]);
});

function intake_frames() { return panel.framesFromResponse(json("figma_nodes.json")); }

test("picking frames updates the request cost live, before anything is spent", () => {
  let s = run({ type: "figma-seat", seat: "view" });
  const { frames } = intake_frames();
  s = panel.reduce(s, { type: "figma-frames", frames, missing: [] });
  assert.equal(s.figma.picked.length, 0);
  s = panel.reduce(s, { type: "figma-pick", id: "1:2" });
  assert.equal(s.figma.cost.requests, 2);
  assert.match(s.figma.cost.note, /2 of this month's 20 requests/);
  s = panel.reduce(s, { type: "figma-pick", id: "1:2" });          // pick again = unpick
  assert.deepEqual(s.figma.picked, []);
  assert.equal(s.figma.cost, null);
});

test("importing is blocked when nothing is picked, and when the seat cannot afford it", () => {
  const { frames } = intake_frames();
  let s = run({ type: "figma-seat", seat: "view" }, { type: "figma-frames", frames, missing: [] });
  assert.equal(panel.view(s).canImport, false);
  s = panel.reduce(s, { type: "figma-pick", id: "1:3" });
  assert.equal(panel.view(s).canImport, true);
  const many = Array.from({ length: 1500 }, (_, i) => ({ id: `${i}:1`, name: `f${i}`, width: 100, height: 100 }));
  s = run({ type: "figma-seat", seat: "view" }, { type: "figma-frames", frames: many, missing: [] }, { type: "figma-pick-all" });
  assert.equal(panel.view(s).canImport, false);
  assert.match(s.figma.error, /view seats get 20 a month/);
});

// --- the token --------------------------------------------------------------------------------

test("the interface never receives the token, only that one is set and its last four characters", () => {
  const s = run({ type: "open", door: "figma" }, { type: "figma-token", token: TOKEN });
  const v = panel.view(s);
  assert.equal(v.figma.hasToken, true);
  assert.equal(v.figma.token, "••••_9f3a".replace("_9f3a", "9f3a").replace("••••9f3a", "••••" + TOKEN.slice(-4)));
  assert.equal(JSON.stringify(v).includes(TOKEN), false, "the full token must not appear anywhere in the view");
  assert.equal(JSON.stringify(v).includes("SECRETSECRET"), false);
});

test("a short token is hidden entirely, since four characters of it would be most of it", () => {
  assert.equal(panel.mask("abcd1234"), "••••");
  assert.equal(panel.mask(""), null);
});

test("closing the panel forgets the token and the queue, but keeps what was already placed", () => {
  let s = run(
    { type: "open", door: "figma" }, { type: "figma-token", token: TOKEN },
    { type: "files", files: [{ name: "a.png", bytes: file("a.png") }] },
  );
  s = panel.reduce(s, { type: "placed", ids: [s.queue[0].id], elements: [{ kind: "image", label: "a" }] });
  s = panel.reduce(s, { type: "figma-token", token: TOKEN });
  s = panel.reduce(s, { type: "close" });
  assert.equal(s.figma.token, "");
  assert.equal(JSON.stringify(s).includes(TOKEN), false);
  assert.equal(s.placed.length, 1);
  assert.equal(s.open, false);
});

test("the client sends the token to api.figma.com and to nothing else", async () => {
  const calls = [];
  const fetchFn = async (url, init) => { calls.push({ url, headers: init?.headers }); return { ok: true, status: 200, json: async () => ({}) }; };
  const client = panel.figmaClient({ token: TOKEN, fetchFn });
  await client.nodes("AbC123xyz789QWERTY", ["1:2"]);
  await client.images("AbC123xyz789QWERTY", ["1:2"], 2);
  assert.equal(calls.length, 2);
  for (const c of calls) {
    assert.equal(new URL(c.url).origin, "https://api.figma.com");
    assert.equal(c.headers["X-Figma-Token"], TOKEN);
  }
});

test("a hostile file key or node id is refused before any request exists", async () => {
  // a key is spliced into a path from a link someone pasted. "a/../../x" would fetch /v1/x, and
  // "//evil.example" would put a second host in the path, so the client checks the shape of the
  // key and the ids and not just the origin it ends up at.
  const sent = [];
  const client = panel.figmaClient({ token: TOKEN, fetchFn: async (u) => { sent.push(u); return { ok: true, status: 200, json: async () => ({}) }; } });
  for (const bad of ["//evil.example", "..//evil.example", "a/../../x", "AbC123", "AbC123xyz789/../x", "", "AbC123xyz789 QWERTY", "AbC123xyz789?x=1"]) {
    await assert.rejects(client.file(bad), /is not a figma file key/, JSON.stringify(bad));
    await assert.rejects(client.images(bad, ["1:2"]), /is not a figma file key/, JSON.stringify(bad));
  }
  for (const bad of ["1:2/../x", "abc", "1:2&format=svg", "1-2", "../1:2"]) {
    await assert.rejects(client.nodes("AbC123xyz789QWERTY", [bad]), /is not a figma node id/, JSON.stringify(bad));
  }
  await assert.rejects(client.images("AbC123xyz789QWERTY", ["1:2"], 9), /outside figma's 0.01 to 4/);
  assert.equal(sent.length, 0, "no request may exist for any hostile input");
});

test("every request any client method can make is on api.figma.com, whatever it is given", async () => {
  // the origin guard in get() is now behind the key and id checks, so it cannot be reached by a
  // hostile argument, which is the point. what remains provable is the invariant: across a spread
  // of keys, ids and scales, valid or not, no request that reaches fetch is anywhere but figma.
  const sent = [];
  const client = panel.figmaClient({ token: TOKEN, fetchFn: async (u, i) => { sent.push([u, i.headers["X-Figma-Token"]]); return { ok: true, status: 200, json: async () => ({}) }; } });
  const keys = ["AbC123xyz789QWERTY", "//evil.example", "a/../../x", "https://evil.example", "AbC123xyz789/.."];
  const ids = [["1:2"], ["1:2/../x"], ["//evil"], ["1:2;3:4"]];
  for (const k of keys) for (const i of ids) for (const call of [() => client.nodes(k, i), () => client.images(k, i, 2), () => client.file(k)]) {
    await call().catch(() => {});
  }
  assert.ok(sent.length > 0, "the valid combinations should have gone through");
  for (const [url, token] of sent) {
    assert.equal(new URL(url).origin, "https://api.figma.com");
    assert.equal(token, TOKEN);
  }
});

test("a real key and real ids still go through, including a nested instance id", async () => {
  const sent = [];
  const client = panel.figmaClient({ token: TOKEN, fetchFn: async (u) => { sent.push(u); return { ok: true, status: 200, json: async () => ({}) }; } });
  await client.nodes("AbC123xyz789QWERTY", ["1:2", "1:2;3:4"]);
  assert.equal(sent[0], "https://api.figma.com/v1/files/AbC123xyz789QWERTY/nodes?ids=1%3A2%2C1%3A2%3B3%3A4&depth=2");
});

test("downloading an exported image does not use the figma client, so no token goes to storage", async () => {
  const seen = [];
  const { frames } = intake_frames();
  const fetchFn = async (url) => {
    seen.push(url);
    return { ok: true, status: 200, json: async () => json("figma_images.json") };
  };
  const client = panel.figmaClient({ token: TOKEN, fetchFn });
  const downloads = [];
  const out = await panel.importPicked({
    client, parsed: { fileKey: "AbC123xyz789QWERTY" }, frames, picked: ["1:2", "1:3"],
    download: async (u) => { downloads.push(u); return file("a.png"); }, seat: "view",
  });
  assert.equal(out.elements.length, 2);
  assert.equal(downloads.length, 2);
  assert.equal(downloads.every((u) => u.startsWith("https://s3-alpha.figma.com/")), true);
  assert.equal(JSON.stringify(out).includes(TOKEN), false);
});

test("figma's status codes become plain sentences, and 429 says the budget may be spent", async () => {
  const mk = (status, headers = {}) => panel.figmaClient({ token: TOKEN, fetchFn: async () => ({ ok: false, status, headers: { get: (k) => headers[k] ?? null }, json: async () => ({}) }) });
  await assert.rejects(mk(403).file("AbC123xyz789QWERTY"), /rejected the token, or it cannot see this file/);
  await assert.rejects(mk(404).file("AbC123xyz789QWERTY"), /could not find that file or node/);
  await assert.rejects(mk(429, { "retry-after": "42" }).file("AbC123xyz789QWERTY"), /retry in 42s.*budget may be spent/);
  await assert.rejects(mk(500).file("AbC123xyz789QWERTY"), /answered 500/);
});

test("a client cannot be made without a token", () => {
  assert.throws(() => panel.figmaClient({ token: "" }), /token is needed/);
});

test("an import issues one images call per fifty frames, not one per frame", async () => {
  const many = Array.from({ length: 120 }, (_, i) => ({ id: `${i}:1`, name: `f${i}`, width: 400, height: 300 }));
  const calls = [];
  const client = {
    images: async (_k, ids) => { calls.push(ids.length); return { err: null, images: Object.fromEntries(ids.map((id) => [id, `https://s3-alpha.figma.com/${id}`])) }; },
  };
  const out = await panel.importPicked({
    client, parsed: { fileKey: "k" }, frames: many, picked: many.map((f) => f.id),
    download: async () => file("a.png"), seat: "dev",
  });
  assert.deepEqual(calls, [50, 50, 20]);
  assert.equal(out.requests, 3);
  assert.equal(out.elements.length, 120);
});

test("an oversize frame in a batch lowers that batch's scale so figma never shrinks it silently", async () => {
  const frames = [{ id: "1:1", name: "small", width: 800, height: 600 }, { id: "1:2", name: "huge", width: 6000, height: 4000 }];
  let scale;
  const client = { images: async (_k, ids, s) => { scale = s; return { err: null, images: Object.fromEntries(ids.map((id) => [id, "https://s3-alpha.figma.com/x"])) }; } };
  await panel.importPicked({ client, parsed: { fileKey: "k" }, frames, picked: ["1:1", "1:2"], download: async () => file("a.png"), seat: "dev" });
  assert.ok(scale < 2, `scale ${scale} would put the huge frame over 32 megapixels`);
});

// --- the source itself -----------------------------------------------------------------------

test("the panel code has no way to persist or log a token", () => {
  const src = fs.readFileSync(path.join(here, "..", "src", "panel.mjs"), "utf8")
    .split("\n").filter((l) => !l.trim().startsWith("*") && !l.trim().startsWith("//")).join("\n");
  assert.equal(/localStorage|sessionStorage|indexedDB|document\.cookie|console\.(log|debug|info|warn)/.test(src), false);
  assert.equal(/location\.(search|hash)|history\.(push|replace)State/.test(src), false);
});
