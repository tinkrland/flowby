/**
 * Card: one node, drawn as fuser draws it. a thin skin over nodeui.mjs, which decides every row.
 *
 * header (title, kind), then one row per port or property with its socket on the card edge, a
 * fold line when properties are hidden, and for an element the picture as the body, so the node
 * is its own preview. a selected node gets a soft glow and a small action bar under it, and
 * nothing else on the canvas is saturated except the wires.
 *
 * dark only. the neutrals are the same ones the panel uses, and the only hues are the wire hues
 * that nodeui hands back per row.
 */

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { m, useReducedMotion } from "motion/react";
import { useState } from "react";

import { nodeEnter, nodeHover } from "./anim.mjs";
import { CARD, SOCKET, actionsFor, cardOf, socketOpacity } from "./nodeui.mjs";
import type { CardRow } from "./nodeui.mjs";

const N = {
  card: "#101012", line: "#1f1f23", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa",
  glow: "rgba(167,139,250,0.55)", accent: "#a78bfa", rowHover: "#16161a",
};

type Row = CardRow;

/** a socket: a circle for one connection, an oval for many, in the colour of what it carries. */
function Socket({ row, side, top }: { row: Row; side: "in" | "out"; top: number }) {
  const shape = SOCKET[row.shape ?? "circle"];
  return (
    <Handle
      id={`${side}:${row.name}`}
      type={side === "in" ? "target" : "source"}
      position={side === "in" ? Position.Left : Position.Right}
      title={`${row.dtype}${row.role ? ` / ${row.role}` : ""}${row.shape === "oval" ? ", takes many" : ""}`}
      style={{
        position: "absolute",
        // react flow translates a handle by half its own size on top of this, so ask for the row's
        // centre and let it do that half and not both. measured: sockets were 3px high and inputs
        // 2px inside the edge while outputs were 4px outside, which is two different offsets.
        top: top,
        transform: side === "in" ? "translate(-50%, -50%)" : "translate(50%, -50%)",
        [side === "in" ? "left" : "right"]: 0,
        width: shape.w,
        height: shape.h,
        borderRadius: shape.w,
        background: row.hex,
        opacity: socketOpacity(row),
        border: `2px solid ${N.card}`,
        // a role rides the wire, so the socket is hollow-ringed to say it is not a plain image
        boxShadow: row.role ? `0 0 0 1px ${row.hex}` : "none",
      }}
    />
  );
}

function RowView({ row, y }: { row: Row; y: number }) {
  const isProp = row.side === "prop";
  return (
    <div
      style={{
        position: "relative",
        height: CARD.row,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 14px",
        fontSize: 11,
        color: row.side === "out" ? N.text : N.dim,
      }}
    >
      {row.side === "in" && <Socket row={row} side="in" top={CARD.row / 2} />}
      <span>{row.name}{row.role ? <span style={{ color: N.mute }}> · {row.role}</span> : null}</span>
      {isProp && <span style={{ color: N.text, fontVariantNumeric: "tabular-nums" }}>{row.value}</span>}
      {row.side === "out" && <Socket row={row} side="out" top={CARD.row / 2} />}
      <span hidden>{y}</span>
    </div>
  );
}

export function Card({ id, data, selected }: NodeProps) {
  const reduced = useReducedMotion() ?? false;
  const [open, setOpen] = useState(false);
  const preview = (data.preview as string | undefined) ?? undefined;
  const card = cardOf(
    { id, op: String(data.op), label: String(data.label), inputs: data.inputs as any, outputs: data.outputs as any, params: data.params as any },
    { expanded: open, connected: new Set((data.connected as string[] | undefined) ?? []) },
  );
  const actions = actionsFor({ op: String(data.op) } as any);
  let y = CARD.head;

  return (
    <m.div
      {...nodeEnter(Number(data.rank) || 0, { reduced })}
      {...nodeHover({ reduced })}
      data-selected={selected ? "true" : "false"}
      style={{
        width: CARD.width,
        borderRadius: 12,
        background: N.card,
        // no border at rest: the card is separated from the canvas by contrast alone, as in fuser.
        // selection is a ring, so it is the only thing on the canvas that has an outline.
        border: "1px solid transparent",
        outline: selected ? "1px solid rgba(167,139,250,0.55)" : "none",
        outlineOffset: 1,
        boxShadow: selected ? `0 0 0 3px rgba(167,139,250,0.12), 0 8px 28px ${N.glow.replace("0.55", "0.18")}` : "none",
        color: N.text,
        font: "500 12px/1.3 ui-sans-serif, system-ui, sans-serif",
        position: "relative",
        willChange: "transform",
      }}
    >
      <div style={{ height: CARD.head, padding: "8px 14px 0", boxSizing: "border-box" }}>
        <div style={{ fontSize: 12.5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{card.title}</div>
        <div style={{ fontSize: 10, color: N.mute, marginTop: 1 }}>{card.kind}</div>
      </div>

      {card.inputs.map((r: Row) => <RowView key={`i:${r.name}`} row={r} y={(y += CARD.row)} />)}
      {card.properties.map((r: Row) => <RowView key={`p:${r.name}`} row={r} y={(y += CARD.row)} />)}

      {card.foldLabel && (
        <button
          onClick={() => setOpen(true)}
          style={{ display: "block", width: "100%", height: CARD.fold, background: "none", border: 0, color: N.mute, fontSize: 10.5, textAlign: "left", padding: "0 14px", cursor: "pointer" }}
        >
          {card.foldLabel}
        </button>
      )}
      {open && card.hidden === 0 && card.properties.length > 3 && (
        <button
          onClick={() => setOpen(false)}
          style={{ display: "block", width: "100%", height: CARD.fold, background: "none", border: 0, color: N.mute, fontSize: 10.5, textAlign: "left", padding: "0 14px", cursor: "pointer" }}
        >
          fold
        </button>
      )}

      {preview && (
        <div style={{ margin: "0 10px 2px", height: CARD.preview - 6, borderRadius: 8, overflow: "hidden", background: "#0a0a0c" }}>
          <img src={preview} alt={card.title} draggable={false} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        </div>
      )}

      {card.outputs.map((r: Row) => <RowView key={`o:${r.name}`} row={r} y={(y += CARD.row)} />)}
      <div style={{ height: CARD.pad }} />

      {selected && (
        <div
          role="toolbar"
          aria-label={`${card.title} actions`}
          style={{ position: "absolute", left: "50%", top: "100%", transform: "translate(-50%, 8px)", display: "flex", gap: 2, background: "#121214", border: `1px solid ${N.line}`, borderRadius: 10, padding: 3, zIndex: 5 }}
        >
          {actions.map((a: { id: string; label: string; primary?: boolean }) => (
            <button
              key={a.id}
              title={a.label}
              onClick={(e) => { e.stopPropagation(); window.dispatchEvent(new CustomEvent("flowby:action", { detail: { id: a.id, node: id } })); }}
              style={{
                background: a.primary ? N.accent : "none",
                color: a.primary ? "#0b0b0d" : N.dim,
                border: 0, borderRadius: 7, padding: "4px 9px", fontSize: 11, fontWeight: a.primary ? 700 : 500, cursor: "pointer",
              }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </m.div>
  );
}
