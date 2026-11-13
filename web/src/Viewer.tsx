/**
 * Viewer: the graph as text, for a screen too narrow to drag a canvas on.
 *
 * a skin over viewer.mjs. it draws what python put in the graph and nothing else: no thumbnails, no
 * "open" buttons, because there is nothing on a phone that the board would let you do.
 */

import { VIEWER, viewerTotal } from "./viewer.mjs";

const K = {
  bg: "#0b0b0c",
  card: "#141416",
  line: "#26262b",
  text: "#e4e4e7",
  mute: "#8b8b93",
  dim: "#5c5c64",
  accent: "#a78bfa",
};

export type ViewerRow = {
  id: string;
  label: string;
  op: string;
  gpu: boolean;
  known: boolean;
  minutes: number;
  pips: number;
  text: string;
};

export function Viewer({ rows, title }: { rows: ViewerRow[]; title: string }) {
  const total = viewerTotal(rows);
  return (
    <div style={{ overflowY: "auto", padding: "14px 14px 28px", color: K.text }}>
      <p style={{ margin: "0 0 4px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: K.dim }}>{VIEWER.heading}</p>
      <p style={{ margin: "0 0 14px", fontSize: 12, lineHeight: 1.5, color: K.mute }}>{VIEWER.note}</p>

      <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }} aria-label={`${title}, ${rows.length} nodes`}>
        {rows.map((row, index) => (
          <li
            key={row.id}
            style={{ display: "flex", alignItems: "baseline", gap: 10, background: K.card, border: `1px solid ${K.line}`, borderRadius: 10, padding: "10px 12px" }}
          >
            <span style={{ fontSize: 11, color: K.dim, minWidth: 14, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{index + 1}</span>
            <span style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.label}</span>
              <span style={{ fontSize: 11, color: K.dim, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.op}</span>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
              <span aria-hidden style={{ display: "flex", gap: 2 }}>
                {Array.from({ length: row.pips }).map((_, i) => (
                  <span key={i} style={{ width: 3, height: 11, borderRadius: 1, background: row.gpu ? K.accent : K.dim, opacity: row.known ? 1 : 0.3 }} />
                ))}
              </span>
              <span style={{ fontSize: 11, color: row.known ? K.mute : K.dim, fontVariantNumeric: "tabular-nums", minWidth: 0 }}>{row.text}</span>
            </span>
          </li>
        ))}
      </ol>

      <p style={{ margin: "12px 2px 0", fontSize: 11, color: K.dim }}>{total.spoken}</p>
    </div>
  );
}
