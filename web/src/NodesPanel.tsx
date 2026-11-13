/**
 * NodesPanel: the popover the rail's grid slot opens, and the shape the reference board uses.
 *
 * a heading with the keyboard shortcut on the right, one sentence of what the panel is for, then the
 * groups. every group here is a **wire type**, because presets.json declares the type each preset
 * writes and dtypes.py decides which types exist: a group nothing writes cannot appear, and a preset
 * whose output is not declared lands in `other` rather than vanishing.
 *
 * the rows carry what a person needs before pressing: the task name, the types it reads and writes, and
 * the estimated minutes. that is the whole of the reference's card, minus its thumbnail, which this tree
 * cannot honestly draw until a worker has produced a real result.
 */

import { estimateText } from "./rail.mjs";
import type { NodeGroup } from "./rail.d.mts";

const K = { text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", line: "#1f1f23", hover: "#17171b", accent: "#a78bfa" };

export function NodesPanel({ groups, onPick }: { groups: { groups: NodeGroup[]; total: number; empty: string }; onPick: (name: string) => void }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: K.text }}>Nodes</span>
        <kbd style={{ marginLeft: "auto", fontSize: 10.5, color: K.mute, border: `1px solid ${K.line}`, borderRadius: 5, padding: "1px 5px" }}>Shift+A</kbd>
      </div>
      <p style={{ margin: "4px 0 0", color: K.mute, lineHeight: 1.45 }}>Discover nodes and connect them to create your own workflows.</p>
      {groups.total === 0 ? (
        <p style={{ margin: "12px 0 0", color: K.mute }}>no presets were read, so this panel has nothing to offer.</p>
      ) : null}
      {groups.groups.map((group) => (
        <section key={group.dtype} style={{ marginTop: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <span aria-hidden style={{ width: 7, height: 7, borderRadius: 4, background: group.hex }} />
            <span style={{ fontWeight: 600, fontSize: 12.5, color: K.text }}>{group.dtype === "other" ? "other" : `${group.dtype}`}</span>
            <span style={{ color: K.mute, fontSize: 11.5 }}>{group.means}</span>
            <span style={{ marginLeft: "auto", color: K.mute, fontSize: 11.5 }}>{group.count}</span>
          </div>
          <ul style={{ listStyle: "none", margin: "7px 0 0", padding: 0, display: "grid", gap: 5 }}>
            {group.rows.map((row) => (
              <li key={row.name}>
                <button
                  type="button"
                  onClick={() => onPick(row.name)}
                  title={row.blurb}
                  style={{ width: "100%", textAlign: "left", background: "none", border: `1px solid ${K.line}`, borderRadius: 8, padding: "7px 9px", cursor: "pointer", color: K.text }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = K.hover; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "none"; }}
                >
                  <span style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span style={{ fontSize: 12.5 }}>{row.label}</span>
                    <span style={{ marginLeft: "auto", color: K.mute, fontSize: 11 }}>{row.stage}</span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3, fontSize: 10.5, color: K.dim }}>
                    <span>{row.from ?? "?"}</span>
                    <span style={{ color: K.mute }}>to</span>
                    <span style={{ color: row.to ? group.hex : K.mute }}>{row.to ?? "unset"}</span>
                    {row.estimate === null ? (
                      <span style={{ marginLeft: "auto", color: K.mute }}>cost unknown</span>
                    ) : (
                      <span style={{ marginLeft: "auto" }}>{estimateText(row.estimate)}</span>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
