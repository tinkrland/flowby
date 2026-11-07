/**
 * anim.mjs: the motion spec, as data.
 *
 * the animation library is **motion** (Framer Motion 14, MIT). the numbers are here, not in the
 * component, for the same reason the wire colours are in `wires.mjs`: a spec is testable from node
 * with no DOM, and a component that hardcodes `stiffness: 420` is a component nobody can check.
 *
 * what "smooth" is actually made of, and why each piece is here rather than decoration:
 *
 * - **stagger by rank.** the graph arrives left to right because that is the direction execution
 *   flows, so the board grows the way the plan runs. 18ms per rank, capped, so a 20-rank chain does
 *   not take a third of a second to appear.
 * - **a spring, not a duration, for anything you touch.** a spring settles where the pointer leaves
 *   it; a fixed curve snaps and looks borrowed from a keynote.
 * - **edges draw themselves** (`pathLength` 0 to 1). this is the cheapest way to say "these two
 *   nodes are now connected" without a toast, and it is the one thing a static screenshot cannot
 *   show, which is also why the tests below are about the spec rather than the picture.
 * - **prefers-reduced-motion wins, silently.** every function here takes `reduced` and returns a
 *   zero-duration, transform-free spec when it is set. not a shorter animation: no animation. motion
 *   is decoration, and decoration that ignores the OS setting is a bug against a real user.
 */

/**
 * the literal types matter: motion's `Transition` needs `type: "spring"`, not `string`, and a plain
 * .mjs would widen it. the JSDoc is what keeps `tsc` honest about the spec without a build step.
 * @typedef {{ type: "spring", stiffness: number, damping: number, mass: number, delay?: number }} Spring
 * @typedef {{ type: "tween", ease: [number, number, number, number], duration: number }} Draw
 * @typedef {{ duration: number }} Still
 */

/** the spring everything that a pointer can touch uses. stiffness/damping/mass, no duration.
 *  @type {Spring} */
export const SPRING = { type: "spring", stiffness: 420, damping: 34, mass: 0.7 };

/** the easing a drawn line uses. it decelerates into the target, so the wire reads as arriving.
 *  @type {Draw} */
export const DRAW = { type: "tween", ease: [0.22, 1, 0.36, 1], duration: 0.42 };

/** per-rank delay, and the cap on it. 20 ranks is 0.18s, a whole board is under a fifth of a second. */
const STAGGER = 0.018;
const STAGGER_CAP = 0.18;

/**
 * how a node enters: fades up 8px, settles with the spring, staggered by its depth in the graph.
 * @param {number} rank the node's depth, as python reports it
 * @param {{reduced?: boolean}} [options]
 * @returns {{initial: Record<string, number>, animate: Record<string, number>, transition: Spring | Still}}
 */
export function nodeEnter(rank, options = {}) {
  if (options.reduced) {
    return { initial: { opacity: 1 }, animate: { opacity: 1 }, transition: { duration: 0 } };
  }
  const step = Math.max(0, Number(rank) || 0);
  return {
    initial: { opacity: 0, y: 8, scale: 0.985 },
    animate: { opacity: 1, y: 0, scale: 1 },
    transition: { ...SPRING, delay: Math.min(step * STAGGER, STAGGER_CAP) },
  };
}

/**
 * a wire drawing itself from its source to its target.
 * @param {{reduced?: boolean}} [options]
 * @returns {{initial: Record<string, number>, animate: Record<string, number>, transition: Draw | Still}}
 */
export function wireDraw(options = {}) {
  if (options.reduced) {
    return { initial: { pathLength: 1 }, animate: { pathLength: 1 }, transition: { duration: 0 } };
  }
  return { initial: { pathLength: 0 }, animate: { pathLength: 1 }, transition: { ...DRAW } };
}

/**
 * the lift under the pointer. two pixels, and a spring, so it reads as the node noticing you.
 * @param {{reduced?: boolean}} [options]
 * @returns {{whileHover?: Record<string, number>, whileTap?: Record<string, number>, transition?: Spring}}
 */
export function nodeHover(options = {}) {
  if (options.reduced) return {};
  return { whileHover: { y: -2 }, whileTap: { scale: 0.997 }, transition: SPRING };
}
