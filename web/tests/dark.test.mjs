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
const sources = ["src/NodeCanvas.tsx", "src/main.tsx", "src/Panel.tsx", "src/gesture.mjs", "index.html"].map(read).join("\n");

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
