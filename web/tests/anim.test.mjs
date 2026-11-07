/**
 * anim.test.mjs: the motion spec, checked as data.
 *
 * a screenshot cannot test an animation, and a video cannot be asserted on in CI, so the spec is a
 * pure function and these are the properties worth holding:
 *
 * - reduced motion means **no** animation, not a faster one. that is an accessibility requirement,
 *   not a preference, so it gets a test rather than a comment.
 * - a spring and a duration are mutually exclusive in motion. mixing them throws at runtime, which
 *   means it would throw in the browser and not here unless something checks.
 * - the stagger is bounded, because a 20-rank chain that animates in sequence for a second reads as
 *   the app being slow rather than smooth.
 * - and the canvas consumes the spec instead of hardcoding its own numbers, which is the only way
 *   this file stays the source of truth.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { DRAW, SPRING, nodeEnter, nodeHover, wireDraw } from "../src/anim.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const canvasSource = fs.readFileSync(path.join(here, "../src/NodeCanvas.tsx"), "utf8");

test("reduced motion gets no movement at all, not a shorter movement", () => {
  const enter = nodeEnter(6, { reduced: true });
  assert.equal(enter.transition.duration, 0);
  assert.deepEqual(enter.initial, { opacity: 1 });
  assert.equal(enter.animate.y, undefined, "no transform: the node is simply there");
  assert.equal(enter.animate.scale, undefined);

  const draw = wireDraw({ reduced: true });
  assert.equal(draw.transition.duration, 0);
  assert.equal(draw.initial.pathLength, 1, "the wire is already drawn");

  assert.deepEqual(nodeHover({ reduced: true }), {}, "no hover lift when the OS says so");
});

test("a node enters by rising eight pixels from nothing", () => {
  const enter = nodeEnter(0);
  assert.equal(enter.initial.opacity, 0);
  assert.equal(enter.animate.opacity, 1);
  assert.equal(enter.initial.y, 8);
  assert.equal(enter.animate.y, 0);
});

test("the stagger follows rank and is capped", () => {
  const delays = [0, 1, 3, 8, 19].map((rank) => nodeEnter(rank).transition.delay);
  assert.deepEqual(delays, [...delays].sort((a, b) => a - b), "later ranks never arrive sooner");
  assert.equal(delays[0], 0, "the first rank is immediate");
  assert.ok(delays[4] <= 0.18 + 1e-9, `a deep chain must not stall the board, got ${delays[4]}`);
  assert.ok(delays[4] > delays[3], "and the cap must not be reached so early that rank stops mattering");
});

test("a negative or missing rank still animates, at zero delay", () => {
  for (const rank of [-4, undefined, null, Number.NaN]) {
    const enter = nodeEnter(rank);
    assert.equal(enter.transition.delay, 0, `rank ${String(rank)} produced a bad delay`);
  }
});

test("springs do not carry a duration, and tweens do", () => {
  const spring = nodeEnter(2).transition;
  assert.equal(spring.type, "spring");
  assert.equal("duration" in spring, false, "motion throws when a spring also has a duration");
  assert.ok(spring.stiffness > 0 && spring.damping > 0 && spring.mass > 0);

  for (const tween of [DRAW, wireDraw().transition]) {
    assert.equal(tween.type, "tween");
    assert.ok(tween.duration > 0);
    assert.equal("stiffness" in tween, false);
  }
  assert.deepEqual(SPRING.ease, undefined);
});

test("a wire draws from nothing to fully drawn, and follows the source to the target", () => {
  const draw = wireDraw();
  assert.equal(draw.initial.pathLength, 0);
  assert.equal(draw.animate.pathLength, 1);
  assert.ok(draw.transition.duration < 0.6, "a wire that takes a second reads as lag");
  assert.equal(draw.initial.opacity, undefined, "the line should not also fade: one idea at a time");
});

test("the spec is deterministic", () => {
  assert.deepEqual(nodeEnter(4), nodeEnter(4));
  assert.deepEqual(wireDraw(), wireDraw());
});

test("the canvas consumes the spec instead of choosing its own numbers", () => {
  assert.match(canvasSource, /from "\.\/anim\.mjs"/);
  assert.match(canvasSource, /useReducedMotion/, "the OS setting has to reach the spec");
  assert.match(canvasSource, /nodeEnter\(|wireDraw\(|nodeHover\(/);
  for (const magic of ["stiffness:", "damping:", "pathLength"]) {
    assert.equal(
      canvasSource.includes(magic),
      false,
      `NodeCanvas.tsx hardcodes ${magic}; the numbers belong in anim.mjs where they are tested`,
    );
  }
});
