/**
 * graph.mjs: the seam between python's graph and @xyflow's canvas.
 *
 * python decides what exists and what is wired to what. it does **not** decide where a node sits:
 * `scene.pipeline()` emits `rank` (depth, which becomes a column) and `row` (which element the node
 * hangs off), and this file turns those into pixels with `@dagre`, an MIT layered layout engine.
 *
 * the alternative was the thing this repo was doing an hour ago: a grid of magic numbers in python,
 * a second layout pass in the renderer, and two systems disagreeing about where everything is. so
 * the rule here is that geometry has exactly one owner, and it is the renderer.
 *
 * everything in this file is a pure function over plain JSON, which is why `tests/graph.test.mjs`
 * can call it from node with no DOM and no React. `NodeCanvas.tsx` is the thin React skin on top.
 */

import dagre from "@dagrejs/dagre";
import { CARD, cardHeight, cardOf } from "./nodeui.mjs";
import { portStyle, wireFor } from "./wires.mjs";

/**
 * a node box, in css pixels, before dagre gets involved. the card owns its own geometry
 * (nodeui.CARD), and layout asks it, so the box dagre places and the card that is drawn cannot
 * disagree about how big a node is.
 */
export const NODE_W = CARD.width;

/**
 * how tall a node has to be. react flow measures dom, but dagre needs the number up front, and it
 * has to be the same one the card is drawn at.
 * @param {any} node
 * @param {{expanded?: boolean, preview?: boolean}} [options]
 */
export function nodeHeight(node, options = {}) {
  return cardHeight(cardOf(node, { expanded: options.expanded }), { preview: options.preview });
}

/** stable id for a wire, so react flow can reconcile rather than remount */
const edgeId = (wire) => `${wire.from.node}:${wire.from.port}->${wire.to.node}:${wire.to.port}`;

/**
 * check every wire against the nodes before anything is drawn.
 *
 * a dangling wire is the failure mode that renders as a very quiet line to nowhere, so it refuses
 * with the port named instead. same argument as the compiler's refusals, one layer up.
 * @param {{nodes: any[], wires: any[]}} pipeline
 */
export function check(pipeline) {
  const byId = new Map(pipeline.nodes.map((n) => [n.id, n]));
  const seen = new Set();
  for (const wire of pipeline.wires) {
    for (const [end, ports] of [
      [wire.from, "outputs"],
      [wire.to, "inputs"],
    ]) {
      const node = byId.get(end.node);
      if (!node) throw new Error(`wire ${edgeId(wire)} points at a node that is not on the board`);
      if (!(end.port in node[ports])) {
        throw new Error(
          `wire ${edgeId(wire)} points at ${end.node}.${end.port}, which is not one of its ${ports}`,
        );
      }
    }
    const id = edgeId(wire);
    if (seen.has(id)) throw new Error(`two wires share the shape ${id}`);
    seen.add(id);
    // the wire's colour comes from the port it leaves, because that is what the value is
    const dtype = byId.get(wire.from.node).outputs[wire.from.port].dtype;
    if (wire.dtype && wire.dtype !== dtype) {
      throw new Error(`${id} is labelled ${wire.dtype} but leaves a ${dtype} port`);
    }
  }
  return pipeline;
}

/**
 * the board's graph, as react flow wants it.
 *
 * @param {{nodes: any[], wires: any[]}} pipeline
 * @param {{rankdir?: "LR" | "TB", nodesep?: number, ranksep?: number}} [options]
 */
export function toFlow(pipeline, options = {}) {
  check(pipeline);
  const { rankdir = "LR", nodesep = 26, ranksep = 104 } = options;

  const g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({ rankdir, nodesep, ranksep, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));

  // insertion order is dagre's tie-breaker, so sort by the two facts python does own: which
  // element a node hangs off, then its depth. without this the layout jumps between renders.
  const ordered = [...pipeline.nodes].sort(
    (a, b) => a.row - b.row || a.rank - b.rank || a.id.localeCompare(b.id),
  );
  for (const node of ordered) {
    g.setNode(node.id, { width: NODE_W, height: nodeHeight(node) });
  }
  for (const wire of pipeline.wires) {
    g.setEdge(wire.from.node, wire.to.node, { width: 0, height: 0, labelpos: "c" }, edgeId(wire));
  }
  dagre.layout(g);

  const nodes = ordered.map((node) => {
    const box = g.node(node.id);
    return {
      id: node.id,
      // two shapes on the board: what you put there, and what ran on it
      type: node.op.startsWith("element.") ? "element" : "op",
      position: { x: box.x - box.width / 2, y: box.y - box.height / 2 },
      width: box.width,
      height: box.height,
      data: {
        label: node.label,
        op: node.op,
        instance: node.instance,
        rank: node.rank,
        row: node.row,
        params: node.params,
        inputs: node.inputs,
        outputs: node.outputs,
      },
    };
  });

  const edges = pipeline.wires.map((wire) => {
    const port = g.edge(wire.from.node, wire.to.node, edgeId(wire));
    const out = pipeline.nodes.find((n) => n.id === wire.from.node).outputs[wire.from.port];
    const style = portStyle(out);
    return {
      id: edgeId(wire),
      source: wire.from.node,
      target: wire.to.node,
      sourceHandle: `out:${wire.from.port}`,
      targetHandle: `in:${wire.to.port}`,
      type: "wire",
      // a role rides a wire without being interchangeable with a plain one, so it is dashed
      data: {
        dtype: out.dtype,
        colour: wireFor(out.dtype).colour,
        hex: style.stroke,
        role: style.role,
        dashed: style.dashed,
        points: port?.points ?? [],
      },
    };
  });

  return {
    nodes,
    edges,
    extent: {
      width: (g.graph().width ?? 0) + 48,
      height: (g.graph().height ?? 0) + 48,
    },
  };
}
