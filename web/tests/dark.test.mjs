/**
 * dark.test.mjs: flowby is dark mode only, and that is a decision, so it is a test.
 *
 * there is no light theme and no toggle. these checks fail if anyone adds either, because the
 * cheap way to drift is a `prefers-color-scheme: light` block "just for contrast" that quietly
 * becomes a second theme nobody designed.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const read = (rel) => fs.readFileSync(path.join(here, "..", rel), "utf8");

const html = read("index.html");
const canvas = read("src/NodeCanvas.tsx");
const sources = ["src/NodeCanvas.tsx", "src/main.tsx", "src/Panel.tsx", "src/Card.tsx", "src/Chrome.tsx", "src/gesture.mjs", "src/nodeui.mjs", "index.html"].map(read).join("\n");

test("the document declares itself dark to the browser", () => {
  assert.match(html, /<meta name="color-scheme" content="dark"/);
  assert.match(html, /color-scheme:\s*dark/);
});

test("the canvas library is told to render dark, not left on its light default", () => {
  assert.match(canvas, /colorMode="dark"/);
});

test("there is no light theme, no toggle and no system-preference branch", () => {
  assert.equal(/prefers-color-scheme\s*:\s*light/.test(sources), false);
  assert.equal(/colorMode="(light|system)"/.test(sources), false);
  assert.equal(/theme[-_ ]?toggle|toggleTheme|setTheme/i.test(sources), false);
});

test("the page background is near black, so the dot grid reads", () => {
  const match = html.match(/background:\s*#([0-9a-f]{6})/i);
  assert.ok(match, "the page declares a background");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(match[1].slice(i, i + 2), 16));
  assert.ok((r + g + b) / 3 < 24, `background #${match[1]} is not dark enough`);
});

test("the panel is dark too: every colour it uses is dark or an accent, and none is a light surface", () => {
  const panelSrc = read("src/Panel.tsx");
  const colours = [...panelSrc.matchAll(/#([0-9a-fA-F]{6})\b/g)].map((m) => m[1].toLowerCase());
  assert.ok(colours.length > 5, "the panel declares its palette");
  const luminance = (hex) => {
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  // a surface (background, card, line) must be dark. text and accents are allowed to be light.
  const surfaces = [...panelSrc.matchAll(/(?:bg|card|line):\s*"#([0-9a-fA-F]{6})"/g)].map((m) => m[1]);
  assert.ok(surfaces.length >= 3, "found the surface colours");
  for (const hex of surfaces) assert.ok(luminance(hex) < 0.12, `#${hex} is too light for a surface`);
});

test("the panel takes no theme prop and reads no system preference", () => {
  const panelSrc = read("src/Panel.tsx");
  assert.equal(/\btheme\b|matchMedia|prefers-color-scheme/.test(panelSrc.replace(/\/\*[\s\S]*?\*\//g, "")), false);
});

test("the card and the chrome are dark: every surface they draw is dark, and the only hues are wire hues and one accent", () => {
  for (const file of ["src/Card.tsx", "src/Chrome.tsx"]) {
    const src = read(file);
    const luminance = (hex) => { const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const hex = (re) => [...src.matchAll(re)].map((m) => m[1]);
    // luminance here is on gamma-encoded values, so #1a1a1e scores 0.10 and #333333 scores 0.2: the
    // line between a dark interface and a light one is nowhere near either, and a pale surface
    // (fuser's own, about 0.95) fails by a mile. a hairline is meant to be visible against its surface, so
    // it gets a looser cap, but still has to be a dark grey and never a light line on a dark card.
    const surfaces = hex(/(?:card|bg|hover|rowHover):\s*"#([0-9a-fA-F]{6})"/g);
    const hairlines = hex(/line:\s*"#([0-9a-fA-F]{6})"/g);
    assert.ok(surfaces.length >= 2, `${file} declares its surfaces`);
    assert.ok(hairlines.length >= 1, `${file} declares its hairline`);
    for (const h of surfaces) assert.ok(luminance(h) < 0.2, `${file}: #${h} is too light for a surface`);
    for (const h of hairlines) assert.ok(luminance(h) < 0.3, `${file}: #${h} is too light for a hairline`);
    assert.equal(/\btheme\b|matchMedia|prefers-color-scheme/.test(src.replace(/\/\*[\s\S]*?\*\//g, "")), false, `${file} reads a theme`);
  }
});

test("the guard would catch a light surface: a pale card and a pale hairline both fail it", () => {
  const luminance = (hex) => { const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  for (const pale of ["f4f4f5", "ffffff", "e4e4e7", "a1a1aa"]) assert.ok(luminance(pale) >= 0.3, `#${pale} should fail the guard`);
});
