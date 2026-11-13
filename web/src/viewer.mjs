/**
 * viewer.mjs: what a phone shows instead of the board, decided without a DOM.
 *
 * measured on 2026-11-12: at 390px wide the board fits seven nodes at **21% zoom**, so the cards are
 * unreadable before anything is selected. fuser's answer to the same problem is to not open its editor
 * on a phone at all: compositor nodes still display their output, the editor does not open
 * (docs/compositor/concepts.md). that is the rule taken here, and it is cheaper than a phone layout
 * for a canvas whose whole point is dragging things.
 *
 * so a narrow screen gets the graph as text: one row per node, in graph order, with the same price the
 * pill would charge. nothing is invented and nothing is hidden: the row count is the node count.
 */

/** below this width the board is a viewer, not an editor. fuser draws the line at tablet. */
export const EDITOR_MIN_WIDTH = 760;

export function isNarrow(width) {
  return Number.isFinite(width) ? width < EDITOR_MIN_WIDTH : false;
}

/** the exact words the viewer prints. one place, so the page and the tests cannot disagree. */
export const VIEWER = Object.freeze({
  heading: "the graph, as text",
  note: "the board runs on a desktop or tablet browser. here it is as a list, with the same price each node would cost.",
});

export function minutesText(minutes) {
  if (!Number.isFinite(minutes)) return "cost unknown";
  if (minutes <= 0) return "free";
  return `${Number(minutes.toFixed(1))} min`;
}

/**
 * one row per node, in graph order. a node with no `cost` block reads `cost unknown`, never `free`,
 * for the same reason selection.mjs refuses a confident zero.
 */
export function viewerRows(nodes) {
  return (nodes ?? []).map((node) => {
    const cost = node?.cost;
    const known = Boolean(cost && Number.isFinite(cost.minutes));
    const minutes = known ? cost.minutes : NaN;
    return {
      id: node?.id ?? "",
      label: node?.label || node?.op || node?.id || "",
      op: node?.op ?? "",
      gpu: known ? cost.gpu === true : false,
      known,
      minutes,
      pips: known ? Math.max(0, Math.ceil(minutes)) : 0,
      text: minutesText(minutes),
    };
  });
}

/** the total, phrased for one line under the list. an unknown among them makes the total a floor. */
export function viewerTotal(rows) {
  const list = rows ?? [];
  const timed = list.filter((r) => r.known);
  const minutes = timed.reduce((sum, r) => sum + (r.minutes || 0), 0);
  const unknown = list.length - timed.length;
  const text = `${Number(minutes.toFixed(1))} min`;
  return {
    minutes,
    unknown,
    text,
    spoken: unknown > 0 ? `${text} at least, ${unknown} not counted` : `${text} across ${list.length} nodes`,
  };
}
