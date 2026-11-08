/**
 * NodeCanvas: the node layer, drawn by @xyflow rather than by hand.
 *
 * this file is deliberately thin. everything that can be wrong about the graph itself is in
 * `graph.mjs` (pure, tested in node) or in python (the graph). what lives here is the part that
 * needs a DOM: two node shapes, one edge shape, and the camera handshake with the spatial layer.
 *
 * why @xyflow and not something bespoke: it is MIT, it is the node editor react developers already
 * know, it gives handles, subflows, a minimap, a grid, keyboard and accessible roles for free, and
 * its viewport is `screen = page * zoom + translate`, which is the exact shape `align.mjs` already
 * converts. so the node canvas and the tldraw canvas can share one camera with the function that
 * already exists.
 *
 * state: designed. it typechecks and it bundles; nobody has dragged a node yet.
 */

import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  applyNodeChanges,
  type NodeChange,
  getBezierPath,
  type EdgeProps,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { LazyMotion, domAnimation, m, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { cameraFromTldraw } from "./align.mjs";
import { wireDraw } from "./anim.mjs";
import { Card } from "./Card";
import { toFlow } from "./graph.mjs";

type Port = { dtype: string; role?: string | null; many?: boolean };

/** one wire: a bezier in its dtype's colour, dashed when a role rides it. */
export function WireEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const reduced = useReducedMotion() ?? false;
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });
  const dashed = Boolean(data?.dashed);
  return (
    <m.path
      className="react-flow__edge-path"
      d={path}
      {...wireDraw({ reduced })}
      style={{
        stroke: String(data?.hex ?? "#52525b"),
        strokeWidth: 1.5,
        strokeDasharray: dashed ? "5 4" : undefined,
        opacity: dashed ? 0.75 : 0.95,
      }}
    />
  );
}

// both shapes are one card: what you put there and what ran on it differ in their rows, not their chrome
const nodeTypes = { op: Card, element: Card };
const edgeTypes = { wire: WireEdge };

export type NodeCanvasProps = {
  /** the `pipeline` block of `flowby --json graph`. python owns this shape. */
  pipeline: { nodes: any[]; wires: any[] };
  /** the spatial layer's camera, so the two canvases can agree about where things are. */
  onCameraChange?: (camera: { x: number; y: number; z: number }) => void;
  /** ids of the selected nodes, so the toolbar can decide whether Execute shows. */
  onSelect?: (ids: string[]) => void;
  /** a drag from a socket that ended on empty space: the host opens quick connect there. */
  onQuickConnect?: (drop: { side: "in" | "out"; dtype: string; role: string | null; x: number; y: number }) => void;
  /** pictures to show as a card's body, by node id. */
  previews?: Record<string, string>;
};

export function NodeCanvas({ pipeline, onCameraChange, onSelect, onQuickConnect, previews }: NodeCanvasProps) {
  const flow = useMemo(() => {
    const laid = toFlow(pipeline);
    if (!previews) return laid;
    return { ...laid, nodes: laid.nodes.map((n: any) => (previews[n.id] ? { ...n, data: { ...n.data, preview: previews[n.id] } } : n)) };
  }, [pipeline, previews]);

  // react flow is controlled here: it reports a click, a drag or a selection as a change and waits
  // for us to apply it. with static nodes nothing ever applied them, so a click selected nothing.
  // positions and selection are view state, so they live here and python never hears of them.
  const [nodes, setNodes] = useState<any[]>(flow.nodes);
  useEffect(() => {
    // a new graph from python replaces the layout but keeps what is selected
    setNodes((old) => flow.nodes.map((n: any) => ({ ...n, selected: old.find((o) => o.id === n.id)?.selected ?? false })));
  }, [flow]);
  const onNodesChange = useCallback((changes: NodeChange[]) => setNodes((all) => applyNodeChanges(changes, all)), []);

  return (
    <LazyMotion features={domAnimation} strict>
      <ReactFlow
        colorMode="dark"
        nodes={nodes}
        onNodesChange={onNodesChange}
        edges={flow.edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        minZoom={0.15}
        maxZoom={2}
        snapToGrid
        snapGrid={[8, 8]}
        panOnScroll
        // the board is the product: dragging a node is a view preference, not data, so it stays
        // local until positions are something python is willing to store
        nodesDraggable
        onSelectionChange={({ nodes }: { nodes: { id: string }[] }) => onSelect?.(nodes.map((n) => n.id))}
        onConnectEnd={(event: MouseEvent | TouchEvent, state: any) => {
          // a drag that did not land on a socket is quick connect, as in fuser: the menu opens where
          // the pointer let go and lists only what could be wired to the socket it left
          if (state?.isValid || !state?.fromHandle) return;
          const [side, ] = String(state.fromHandle.id).split(":");
          const nodeData = flow.nodes.find((n: any) => n.id === state.fromNode?.id)?.data as any;
          const port = (side === "out" ? nodeData?.outputs : nodeData?.inputs)?.[String(state.fromHandle.id).split(":")[1]];
          if (!port) return;
          const pt = "changedTouches" in event ? event.changedTouches[0] : (event as MouseEvent);
          onQuickConnect?.({ side: side as "in" | "out", dtype: port.dtype, role: port.role ?? null, x: pt.clientX, y: pt.clientY });
        }}
        onMove={(_event: unknown, viewport: Viewport) => {
          onCameraChange?.(
            cameraFromTldraw({
              x: viewport.x,
              y: viewport.y,
              z: viewport.zoom,
            }),
          );
        }}
      >
        <Background
          variant={BackgroundVariant.Lines}
          gap={24}
          size={1}
          color="#1c1c1f"
        />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(9,9,11,0.85)"
          nodeStrokeWidth={2}
        />
      </ReactFlow>
    </LazyMotion>
  );
}
