/**
 * board.mjs: where the page's board comes from, decided without a DOM.
 *
 * two things can answer: python, at /api/board, which is the board somebody is actually editing; or
 * graph.json, which `npm run graph` writes and which is a snapshot of the demo board. until now the page
 * only read the snapshot, so a button that changed the board on the server changed nothing on the canvas.
 *
 * the rule is the plug's rule: the live thing wins when it really answered, the snapshot is what is left
 * when it did not, and the page says which one it is looking at rather than pretending they are the same.
 * a snapshot is not a fallback that "just works" either: it cannot be edited, so the page must say so.
 */

export const LIVE = "live";
export const SNAPSHOT = "snapshot";

/** does this look like a board python could have drawn? the fields the canvas reads, nothing more. */
export function drawable(doc) {
  const nodes = doc?.pipeline?.nodes;
  const wires = doc?.pipeline?.wires;
  return Array.isArray(nodes) && Array.isArray(wires);
}

/**
 * pick the document to draw, and say why in words the page can show.
 *
 * the live board carries no legend or roles (python does not publish them), and the canvas colours wires
 * from the roles, so those come from the snapshot when the live board has none of its own. taking them
 * from the snapshot is not a lie: the four wires and their roles are constants of the graph model, and
 * the snapshot is where they are written down.
 */
export function choose({ live, snapshot } = {}) {
  const borrowed = drawable(snapshot) ? { legend: snapshot.legend, roles: snapshot.roles } : {};
  if (drawable(live)) {
    return {
      kind: LIVE,
      doc: { ...borrowed, ...live, legend: live.legend ?? borrowed.legend, roles: live.roles ?? borrowed.roles },
      note: "this is python's board, so what you place here is real",
    };
  }
  if (drawable(snapshot)) {
    return {
      kind: SNAPSHOT,
      doc: snapshot,
      note: "python did not answer, so this is the committed demo board: it draws, and nothing can be placed on it",
    };
  }
  return { kind: null, doc: null, note: "no board: run npm run graph, or start flowby's server" };
}

/** what a place action says afterwards. the receipt is python's sentence; this only adds the source. */
export function afterPlacing(receipt, source) {
  const said = receipt?.receipt?.said;
  if (said) return said;
  if (source !== LIVE) return "placed on python's board, and this page is showing the snapshot, so reload to see it";
  return "python took it, and gave no sentence back";
}
