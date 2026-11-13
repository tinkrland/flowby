/**
 * RailPanels: the frame a rail slot's content sits in.
 *
 * the rail is the board's primary control, so a slot either opens something or says why it cannot. this
 * shell is the thing it opens: a heading, one sentence of what the panel is for, then the panel itself.
 * it exists so the kits panel and the gpu plug do not each invent a size and a shadow, and so the two
 * that moved out of the header (2026-11-13) look like the nodes popover they sit beside.
 *
 * the panels inside are the same components the header used to hold, given `embedded`: one implementation,
 * two placements, no second copy of the kits list to drift.
 */

import type { ReactNode } from "react";

const K = { text: "#e4e4e7", mute: "#71717a", line: "#1f1f23" };

export function RailPanel({ title, blurb, children }: { title: string; blurb: string; children: ReactNode }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: K.text }}>{title}</span>
      </div>
      <p style={{ margin: "4px 0 0", color: K.mute, lineHeight: 1.45 }}>{blurb}</p>
      <div style={{ marginTop: 12, borderTop: `1px solid ${K.line}`, paddingTop: 12 }}>{children}</div>
    </div>
  );
}
