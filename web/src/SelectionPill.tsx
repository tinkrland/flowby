/**
 * SelectionPill: the floating bar that appears when something on the board is selected.
 *
 * this is fuser's detail, taken whole (docs/research.md, 2026-11-12): box-select, and a pill floats at
 * the bottom centre holding focus, duplicate, delete, lock, **the cost of the selection**, then "...".
 * the cost sits in the toolbar because a selection is a proposal, and a proposal's price belongs
 * beside the hand that would spend it.
 *
 * the file decides nothing. every word it shows, every enabled state and the price itself come from
 * `selection.mjs`, which is pure and tested in node. this is the dark skin on top.
 */

import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from "motion/react";

import { moreMenu, pill } from "./selection.mjs";

const K = { bg: "#111113", line: "#2a2a30", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa", hover: "#1c1c21" };

/** 16px line glyphs, drawn rather than imported: four icons is not a dependency */
const GLYPH: Record<string, JSX.Element> = {
  focus: (
    <>
      <path d="M6 2H3.5A1.5 1.5 0 0 0 2 3.5V6M10 2h2.5A1.5 1.5 0 0 1 14 3.5V6M6 14H3.5A1.5 1.5 0 0 1 2 12.5V10M10 14h2.5a1.5 1.5 0 0 0 1.5-1.5V10" />
      <rect x="5.5" y="5.5" width="5" height="5" rx="1" />
    </>
  ),
  duplicate: (
    <>
      <rect x="2" y="2" width="8.5" height="8.5" rx="1.5" />
      <path d="M5.5 12.5v1A1.5 1.5 0 0 0 7 15h5.5A1.5 1.5 0 0 0 14 13.5V8a1.5 1.5 0 0 0-1.5-1.5h-1" />
    </>
  ),
  delete: <path d="M3 4.5h10M6.5 4.5V3a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.5M4.5 4.5l.6 8.6a1.2 1.2 0 0 0 1.2 1.1h3.4a1.2 1.2 0 0 0 1.2-1.1l.6-8.6" />,
  lock: (
    <>
      <rect x="3" y="7" width="10" height="7" rx="1.5" />
      <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" />
    </>
  ),
  unlock: (
    <>
      <rect x="3" y="7" width="10" height="7" rx="1.5" />
      <path d="M5.5 7V5a2.5 2.5 0 0 1 4.7-1.2" />
    </>
  ),
};

function Icon({ name }: { name: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {GLYPH[name] ?? GLYPH.focus}
    </svg>
  );
}

export type SelectionPillProps = {
  /** `pill(...)` from selection.mjs: word, title, actions, cost, count */
  model: ReturnType<typeof pill>;
  onAction: (name: string) => void;
  /** the "..." menu: rows from `moreMenu()`, and the one action that works from it */
  moreOpen: boolean;
  onMore: (open: boolean) => void;
  onMorePick: (name: string) => void;
};

export function SelectionPill({ model, onAction, moreOpen, onMore, onMorePick }: SelectionPillProps) {
  const reduced = useReducedMotion() ?? false;
  const rows = moreMenu();
  return (
    <LazyMotion features={domAnimation} strict>
      <div style={{ position: "absolute", left: "50%", bottom: 68, transform: "translateX(-50%)", zIndex: 13, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
        <AnimatePresence>
          {moreOpen && (
            <m.div
              key="more"
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
              transition={{ duration: reduced ? 0 : 0.14 }}
              role="menu"
              aria-label="more selection actions"
              style={{ minWidth: 232, background: K.bg, border: `1px solid ${K.line}`, borderRadius: 12, padding: 5, boxShadow: "0 18px 40px rgba(0,0,0,0.6)" }}
            >
              {rows.map((row) => (
                <button
                  key={row.name}
                  role="menuitem"
                  disabled={!row.enabled}
                  title={row.reason ?? ""}
                  onClick={() => row.enabled && onMorePick(row.name)}
                  style={{ display: "flex", width: "100%", alignItems: "center", justifyContent: "space-between", gap: 10, background: "none", border: 0, borderRadius: 8, padding: "7px 9px", color: row.enabled ? K.text : K.mute, fontSize: 12, textAlign: "left", cursor: row.enabled ? "pointer" : "not-allowed" }}
                >
                  <span>{row.label}</span>
                  {!row.enabled && <span style={{ fontSize: 10, color: K.mute }}>{row.reason}</span>}
                </button>
              ))}
            </m.div>
          )}
        </AnimatePresence>

        <m.div
          initial={reduced ? false : { opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
          role="toolbar"
          aria-label={`${model.word} selected`}
          style={{ display: "flex", alignItems: "center", gap: 2, background: K.bg, border: `1px solid ${K.line}`, borderRadius: 999, padding: "5px 6px", boxShadow: "0 16px 40px rgba(0,0,0,0.62)" }}
        >
          <span style={{ color: K.dim, fontSize: 11, padding: "0 8px 0 6px", whiteSpace: "nowrap" }}>{model.word}</span>
          <span style={{ width: 1, height: 18, background: K.line }} />
          {model.actions.map((action) => (
            <button
              key={action.name}
              title={action.reason ?? action.label}
              aria-label={action.label}
              aria-disabled={!action.enabled}
              onClick={() => action.enabled && onAction(action.name)}
              style={{ width: 30, height: 30, display: "grid", placeItems: "center", background: "none", border: 0, borderRadius: 999, color: action.enabled ? K.dim : "#3f3f46", cursor: action.enabled ? "pointer" : "not-allowed" }}
            >
              <Icon name={action.label} />
            </button>
          ))}
          <span style={{ width: 1, height: 18, background: K.line, margin: "0 4px" }} />
          {/* the price of the proposal, in the unit the compiler actually uses */}
          <span title={model.cost.hint} style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "0 4px", whiteSpace: "nowrap" }}>
            {model.cost.gpu && <span aria-hidden style={{ width: 5, height: 5, borderRadius: 3, background: K.accent }} />}
            <span style={{ fontSize: 11.5, color: model.cost.timed ? K.text : K.mute, fontVariantNumeric: "tabular-nums" }}>{model.cost.text}</span>
          </span>
          <span style={{ width: 1, height: 18, background: K.line, margin: "0 4px" }} />
          <button
            title="more"
            aria-label="more selection actions"
            aria-expanded={moreOpen}
            onClick={() => onMore(!moreOpen)}
            style={{ width: 28, height: 30, background: "none", border: 0, borderRadius: 999, color: moreOpen ? K.text : K.mute, cursor: "pointer", letterSpacing: 1, fontSize: 14 }}
          >
            …
          </button>
        </m.div>
      </div>
    </LazyMotion>
  );
}
