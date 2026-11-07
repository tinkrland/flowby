/**
 * wires.mjs: the four wire colours, for the renderer.
 *
 * `src/flowby/dtypes.py` is the source of truth. this file is a mirror, and mirrors drift, so
 * `tests/graph.test.mjs` runs `bin/flowby --json legend` and fails if the two disagree. that is
 * the whole reason this is a separate small file rather than hex codes sprinkled into components.
 */

/** @typedef {{dtype: string, colour: string, hex: string, means: string}} Wire */

/** @type {Wire[]} */
export const WIRES = [
  { dtype: "text", colour: "amber", hex: "#f59e0b", means: "words" },
  { dtype: "image", colour: "green", hex: "#22c55e", means: "a still" },
  { dtype: "video", colour: "blue", hex: "#3b82f6", means: "stills with time" },
  { dtype: "mesh", colour: "red", hex: "#ef4444", means: "geometry" },
];

/** the roles that ride an image wire. python owns the wording; this owns the tint. */
export const ROLES = ["depth", "mask", "pose", "palette", "style"];

const BY_DTYPE = new Map(WIRES.map((w) => [w.dtype, w]));

/**
 * a wire's colour, or a refusal.
 *
 * refusing matters more than it looks: a fifth dtype arriving in python and not here would
 * otherwise render as an unstyled grey line that nobody notices until a screenshot.
 *
 * @param {string} dtype
 * @returns {Wire}
 */
export function wireFor(dtype) {
  const wire = BY_DTYPE.get(dtype);
  if (!wire) {
    throw new Error(
      `no colour for the ${JSON.stringify(dtype)} wire. wires.mjs knows ${[...BY_DTYPE.keys()].join(", ")}`,
    );
  }
  return wire;
}

/**
 * a role rides an image wire but is not interchangeable with a plain image, so the renderer draws
 * it dashed and labels it. unknown roles are allowed through: the wire is still green.
 *
 * @param {{dtype: string, role?: string | null}} port
 */
export function portStyle(port) {
  const wire = wireFor(port.dtype);
  return {
    stroke: wire.hex,
    dashed: Boolean(port.role),
    role: port.role ?? null,
  };
}
