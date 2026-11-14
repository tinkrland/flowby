/**
 * render.test.mjs: the panel drawn, with a payload shaped like the one python writes.
 *
 * inspector.test.mjs checks the words; this checks that the words reach the page. the failure it is
 * here to catch is the quiet one: a panel that renders, looks fine, and says "0 runs" about a node
 * that has never run, or drops the failure dot because a field moved.
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const here = path.dirname(fileURLToPath(import.meta.url));
// the bundle has to sit inside the package, or node cannot resolve `react` from where it lands
const out = path.join(here, "..", "node_modules", ".cache", "flowby-panel", `panel-${process.pid}.mjs`);
fs.mkdirSync(path.dirname(out), { recursive: true });

const bundled = build({
  entryPoints: [path.join(here, "panel-entry.tsx")],
  bundle: true, format: "esm", platform: "node", outfile: out, jsx: "automatic",
  external: ["react", "react-dom", "react-dom/server"], logLevel: "error",
}).then(() => import(`file://${out}`));

const doc = {
  work: { run: ["stale"], reuse: ["fresh"], minutes: 1.5 },
  nodes: {
    fresh: {
      id: "fresh", op: "image.pass", label: "pass", params: { amount: 0.5 }, minutes: 0.4,
      gpu: false, verdict: "reuse",
      runs: [
        { id: "fresh#1", state: "ok", minutes: 0.4, at: 1_000_000 },
        { id: "fresh#2", state: "failed", minutes: 0.1, at: 1_000_100, note: "oom" },
      ],
    },
    stale: {
      id: "stale", op: "image.diffuse", label: "relight", params: {}, minutes: 1.1, gpu: true,
      verdict: "run", because: "upstream will run again", runs: [],
    },
  },
};

const panelOf = async (id) => {
  const { RenderPanel } = await bundled;
  return renderToStaticMarkup(React.createElement(RenderPanel, { id, doc, onClose: () => {} }));
};

test("a node that has never run says so, and does not draw a row", async () => {
  const html = await panelOf("stale");
  assert.match(html, /never run/);
  assert.match(html, /never run\. a first run costs what the header says\./);
  assert.doesNotMatch(html, /<li/);
});

test("a run that failed is drawn as a failure, not as a success", async () => {
  const html = await panelOf("fresh");
  assert.match(html, /2 runs/);
  assert.match(html, /#f87171/, "the failed run's dot is the bad colour");
  assert.match(html, /#4ade80/, "and the run that worked is the ok colour");
});

test("the board's summary line is on the panel, because it is the fact the panel exists for", async () => {
  const html = await panelOf("fresh");
  assert.match(html, /1 to run \(1\.5 min\), 1 reused/);
});

test("the header says what a run would cost and the history says what one spent", async () => {
  const html = await panelOf("fresh");
  assert.match(html, /0\.4 minutes?/);
  assert.match(html, /0\.4 min<\/span>/);
});

test("an id that is not on the board draws nothing rather than an empty shell", async () => {
  const html = await panelOf("nowhere");
  assert.equal(html, "<em>no panel</em>");
});

// --- the kits menu, drawn ---------------------------------------------------------------------------
// the words are checked in kitsmenu.test.mjs; this checks that the page agrees with them. the failure
// it exists for is a listed style that looks pressable, which would offer a run that cannot happen.

const kitsBundle = build({
  entryPoints: [path.join(here, "kits-entry.tsx")],
  bundle: true, format: "esm", platform: "node", outfile: out.replace("panel-", "kits-"), jsx: "automatic",
  external: ["react", "react-dom", "react-dom/server"], logLevel: "error",
}).then(() => import(`file://${out.replace("panel-", "kits-")}`));

const kit = {
  id: "analog", label: "analog", blurb: "the look of something made by hand",
  members: [
    { id: "cyanotype", label: "cyanotype", blurb: "prussian blue sun prints", parent: null, state: "listed", runnable: false },
    { id: "crayon", label: "crayon", blurb: "waxy pigment that skips the tooth", parent: null, state: "listed", runnable: false, look: "look.crayon", worded: true },
    { id: "ghost", label: "ghost", blurb: "worded but no such look", parent: null, state: "listed", runnable: false, look: "look.ghost", worded: false },
  ],
};

test("a worded member is drawn with one place button, and a listed one with none", async () => {
  const { RenderKit } = await kitsBundle;
  const html = renderToStaticMarkup(React.createElement(RenderKit, { kit }));
  const buttons = html.match(/<button/g) ?? [];
  assert.equal(buttons.length, 1, "exactly one member can be placed, so exactly one button");
  assert.match(html, /put crayon on the board/);
  assert.doesNotMatch(html, /put cyanotype on the board/, "a style with no wording must not offer a button");
});

test("the word beside a member is its true state, and a worded one says what it lacks", async () => {
  const { RenderKit } = await kitsBundle;
  const html = renderToStaticMarkup(React.createElement(RenderKit, { kit }));
  assert.match(html, /worded, not trained/);
  assert.match(html, /listed, not built yet/);
});

test("a member whose look python did not confirm is not placeable, even if it claims one", async () => {
  const { RenderKit } = await kitsBundle;
  const html = renderToStaticMarkup(React.createElement(RenderKit, { kit }));
  assert.doesNotMatch(html, /put ghost on the board/);
});

test("a row that is being placed says so and goes quiet", async () => {
  const { RenderKit } = await kitsBundle;
  const html = renderToStaticMarkup(React.createElement(RenderKit, { kit, placing: "look.crayon" }));
  assert.match(html, /placing…/);
  assert.match(html, /disabled/);
});

test("the header button never claims more than the kits hold", async () => {
  const { KitButton } = await kitsBundle;
  const html = renderToStaticMarkup(React.createElement(KitButton, { kits: [kit] }));
  assert.match(html, /nothing trained yet; 1 of 3 have wording and can be placed/);
  const off = renderToStaticMarkup(React.createElement(KitButton, { kits: [kit], reachable: false }));
  assert.match(off, /server is not running/);
});
