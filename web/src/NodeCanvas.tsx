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
  BaseEdge,
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  getBezierPath,
  type EdgeProps,
  type NodeProps,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

import { cameraFromTldraw } from "./align.mjs";
import { NODE_W, toFlow } from "./graph.mjs";
import { wireFor } from "./wires.mjs";

const HEAD_H = 46;
const PORT_H = 18;

type Port = { dtype: string; role?: string | null; many?: boolean };

/** one port, as a coloured dot with its name. the dot is the handle react flow measures. */
function PortRow({
  name,
  port,
  side,
  index,
}: {
  name: string;
  port: Port;
  side: "in" | "out";
  index: number;
}) {
  const wire = wireFor(port.dtype);
  return (
    <div
      style={{
        height: PORT_H,
        display: "flex",
        alignItems: "center",
        justifyContent: side === "in" ? "flex-start" : "flex-end",
        gap: 6,
        padding: side === "in" ? "0 8px 0 12px" : "0 12px 0 8px",
        fontSize: 11,
        color: "#a1a1aa",
      }}
    >
      {side === "out" && <span>{name}</span>}
      <span
        title={`${wire.colour}${port.role ? ` / ${port.role}` : ""}`}
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: wire.hex,
          opacity: port.role ? 0.85 : 1,
          outline: port.role ? `1px dashed ${wire.hex}` : "none",
          outlineOffset: 2,
        }}
      />
      {side === "in" && <span>{name}</span>}
      <Handle
        id={`${side}:${name}`}
        type={side === "in" ? "target" : "source"}
        position={side === "in" ? Position.Left : Position.Right}
        style={{
          position: "absolute",
          top: HEAD_H + PORT_H * index + PORT_H / 2 - 4,
          [side === "in" ? "left" : "right"]: -4,
          width: 8,
          height: 8,
          background: wire.hex,
          border: "none",
        }}
      />
    </div>
  );
}

function Shell({
  title,
  subtitle,
  accent,
  children,
}: {
  title: string;
  subtitle: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        width: NODE_W,
        borderRadius: 10,
        border: `1px solid #27272a`,
        borderLeft: `3px solid ${accent}`,
        background: "#0b0b0d",
        color: "#e4e4e7",
        font: "500 12px/1.3 ui-sans-serif, system-ui, sans-serif",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "8px 12px 6px" }}>
        <div style={{ fontSize: 12 }}>{title}</div>
        <div style={{ fontSize: 10, color: "#71717a", marginTop: 2 }}>{subtitle}</div>
      </div>
      {children}
    </div>
  );
}

/** a node that ran something. the wire colour on its left edge is what it passed on. */
export function OpNode({ data }: NodeProps) {
  const inputs = Object.entries(data.inputs as Record<string, Port>);
  const outputs = Object.entries(data.outputs as Record<string, Port>);
  const accent = inputs[0] ? wireFor(inputs[0][1].dtype).hex : "#52525b";
  const swept = Object.keys((data.params as Record<string, unknown>) ?? {}).length;
  return (
    <Shell
      title={String(data.label)}
      subtitle={`${String(data.op)}${swept ? ` · ${swept} params` : ""}`}
      accent={accent}
    >
      {inputs.map(([name, port], i) => (
        <PortRow key={name} name={name} port={port} side="in" index={i} />
      ))}
      {outputs.map(([name, port], i) => (
        <PortRow key={name} name={name} port={port} side="out" index={i} />
      ))}
    </Shell>
  );
}

/** a node that is something you put on the board. no inputs: it is where a chain starts. */
export function ElementNode({ data }: NodeProps) {
  const outputs = Object.entries(data.outputs as Record<string, Port>);
  return (
    <Shell title={String(data.label)} subtitle={String(data.op)} accent="#52525b">
      {outputs.map(([name, port], i) => (
        <PortRow key={name} name={name} port={port} side="out" index={i} />
      ))}
    </Shell>
  );
}

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
    <BaseEdge
      path={path}
      style={{
        stroke: String(data?.hex ?? "#52525b"),
        strokeWidth: 1.5,
        strokeDasharray: dashed ? "5 4" : undefined,
        opacity: dashed ? 0.75 : 0.95,
      }}
    />
  );
}

const nodeTypes = { op: OpNode, element: ElementNode };
const edgeTypes = { wire: WireEdge };

export type NodeCanvasProps = {
  /** the `pipeline` block of `flowby --json graph`. python owns this shape. */
  pipeline: { nodes: any[]; wires: any[] };
  /** the spatial layer's camera, so the two canvases can agree about where things are. */
  onCameraChange?: (camera: { x: number; y: number; z: number }) => void;
};

export function NodeCanvas({ pipeline, onCameraChange }: NodeCanvasProps) {
  const flow = useMemo(() => toFlow(pipeline), [pipeline]);

  return (
    <ReactFlow
      nodes={flow.nodes}
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
      onMove={(_event: unknown, viewport: Viewport) => {
        onCameraChange?.(cameraFromTldraw({ x: viewport.x, y: viewport.y, z: viewport.zoom }));
      }}
    >
      <Background variant={BackgroundVariant.Lines} gap={24} size={1} color="#1c1c1f" />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable maskColor="rgba(9,9,11,0.85)" nodeStrokeWidth={2} />
    </ReactFlow>
  );
}
