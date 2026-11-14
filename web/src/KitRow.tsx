/**
 * KitRow: one member of a kit, drawn. it is its own file so the render test can draw a single row
 * without dragging in the fetch, and so the rule that matters lives in one place:
 *
 *   a member that is only a name gets NO control. a worded member gets one button, and that button
 *   says "place", never "run", because placing puts wording on the board and nothing runs until a
 *   model is plugged in.
 *
 * anything else is a menu that looks like it can do more than it can.
 */

import type { KitRow } from "./kitsmenu.mjs";

const N = { line: "#26262a", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa" };

export function KitRowView({ r, placing, onPlace }: { r: KitRow; placing: string | null; onPlace: (look: string) => void }) {
  const busy = placing === r.look;
  return (
    <li style={{ marginLeft: r.depth * 16, padding: "7px 9px", border: `1px solid ${N.line}`, borderRadius: 8, opacity: r.usable ? 1 : 0.72 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
        <span style={{ color: r.usable ? N.text : N.dim }}>{r.label}</span>
        <span style={{ marginLeft: "auto", color: r.usable ? "#4ade80" : N.mute, fontSize: 11.5 }}>{r.word}</span>
      </div>
      <div style={{ color: N.mute, marginTop: 2, lineHeight: 1.4, fontSize: 11.5 }}>{r.blurb}</div>
      {r.placeable && r.look && (
        <button
          onClick={() => onPlace(r.look as string)}
          disabled={placing !== null}
          title={`put ${r.label} on the board: a text node holding the direction, and the preset that reads it`}
          style={{ marginTop: 6, background: busy ? "#3f3f46" : "#27272a", color: busy ? N.mute : N.text, border: `1px solid ${N.line}`, borderRadius: 7, padding: "3px 9px", cursor: placing ? "default" : "pointer", fontSize: 11.5 }}
        >
          {busy ? "placing…" : "place"}
        </button>
      )}
    </li>
  );
}
