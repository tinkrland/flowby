/**
 * Inspector: the contextual panel, the surface per-node history was built for.
 *
 * every decision about what it says lives in inspector.mjs, which is tested under node. this file is
 * only the drawing: a panel on the right edge of the board, a close affordance, the history rows, and
 * the one line that answers "what would running this actually do".
 *
 * dark only, like the rest of the board. no theme prop and no media query.
 */

import { panel, summary } from "./inspector.mjs";

export type Panel = NonNullable<ReturnType<typeof panel>>;
export type Summary = ReturnType<typeof summary>;

const C = {
  card: "#121214", line: "#1c1c1f", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa",
  accent: "#a78bfa", ok: "#4ade80", bad: "#f87171", warn: "#fbbf24",
};

const mono = "ui-monospace, SFMono-Regular, Menlo, monospace";

export function Inspector({ model, board, onClose }: { model: Panel; board: Summary; onClose: () => void }) {
  return (
    <aside
      aria-label={`node ${model.title}`}
      style={{
        position: "absolute", top: 12, right: 12, width: 300, maxHeight: "calc(100% - 24px)",
        overflow: "auto", background: C.card, border: `1px solid ${C.line}`, borderRadius: 12,
        padding: 14, color: C.text, fontSize: 12.5, lineHeight: 1.45,
        boxShadow: "0 12px 32px rgba(0,0,0,.45)", zIndex: 20,
      }}
    >
      <header style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <strong style={{ fontSize: 13.5 }}>{model.title}</strong>
        <span style={{ color: C.mute, fontFamily: mono, fontSize: 11 }}>{model.op}</span>
        <button
          aria-label="close"
          onClick={onClose}
          style={{ marginLeft: "auto", background: "none", border: 0, color: C.mute, cursor: "pointer", fontSize: 14 }}
        >
          ×
        </button>
      </header>

      <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
        <span style={chip}>{model.cost.value} {model.cost.label}</span>
        {model.cost.gpu ? <span style={{ ...chip, color: C.warn }}>gpu</span> : null}
        <span style={{ ...chip, color: model.count ? C.dim : C.mute }}>
          {model.count ? `${model.count} run${model.count === 1 ? "" : "s"}` : "never run"}
        </span>
        {model.cancelled ? <span style={{ ...chip, color: C.bad }}>{model.cancelled} failed</span> : null}
      </div>

      <p style={{ margin: "10px 0 0", color: model.verdict === "reuse" ? C.ok : C.dim }}>
        {model.verdictLine}
      </p>

      <section style={{ marginTop: 12, borderTop: `1px solid ${C.line}`, paddingTop: 10 }}>
        <span style={{ color: C.mute }}>history</span>
        {model.empty ? (
          <p style={{ margin: "6px 0 0", color: C.mute }}>{model.emptyLine}</p>
        ) : (
          <ul style={{ listStyle: "none", margin: "8px 0 0", padding: 0, display: "grid", gap: 6 }}>
            {model.rows.map((row: Panel["rows"][number]) => (
              <li key={row.id} style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                <span
                  title={row.state}
                  style={{ width: 6, height: 6, borderRadius: 3, background: row.state === "ok" ? C.ok : C.bad, flex: "none" }}
                />
                <span style={{ fontFamily: mono, fontSize: 11, color: C.dim }}>{row.id}</span>
                <span style={{ color: C.mute }}>{row.spent} min</span>
                <span style={{ color: C.mute, marginLeft: "auto" }}>{row.at}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {model.params.length > 0 && (
        <section style={{ marginTop: 12, borderTop: `1px solid ${C.line}`, paddingTop: 10 }}>
          <span style={{ color: C.mute }}>settings</span>
          <dl style={{ margin: "6px 0 0", display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 10px" }}>
            {model.params.map((p: Panel["params"][number]) => (
              <div key={p.name} style={{ display: "contents" }}>
                <dt style={{ color: C.dim, fontFamily: mono, fontSize: 11 }}>{p.name}</dt>
                <dd style={{ margin: 0, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{p.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <footer style={{ marginTop: 12, paddingTop: 10, borderTop: `1px solid ${C.line}`, color: C.mute }}>
        {board.line}
      </footer>
    </aside>
  );
}

const chip = {
  border: `1px solid ${C.line}`, borderRadius: 999, padding: "2px 8px", fontSize: 11,
  color: C.dim, fontVariantNumeric: "tabular-nums",
} as const;
