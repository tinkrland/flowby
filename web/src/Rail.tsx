/**
 * Rail: the board's primary control, as five slots and a run.
 *
 * this replaces the bottom-centre toolbar. the toolbar was a pill that floated over the board and
 * held wire-type buttons; the rail is a column on the left edge, which is where the reference board
 * puts its control and where a hand already is when it is dragging on a canvas.
 *
 * the rail draws slots and nothing else. which slot is live comes from rail.mjs, and what a slot
 * *does* is the host's business, so this file never learns what a preset is.
 *
 * dark only: neutrals plus one violet accent, and the wire hues come through the popover's chips.
 */

import { useEffect, useRef } from "react";

import { Icon } from "./Icons";
import type { railState } from "./rail.mjs";

const K = { bg: "#121214", line: "#1f1f23", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa", hover: "#1a1a1e", on: "#1c1c21" };

type State = ReturnType<typeof railState>;

export function Rail({
  state, active, onSlot, onRun, onClose, children,
}: {
  state: State;
  active: string | null;
  onSlot: (id: string) => void;
  onRun: () => void;
  onClose: () => void;
  children?: React.ReactNode;
}) {
  const root = useRef<HTMLDivElement | null>(null);

  // clicking anywhere else closes the popover, the way the reference board behaves
  useEffect(() => {
    if (!active) return;
    const away = (e: MouseEvent) => { if (root.current && !root.current.contains(e.target as Node)) onClose(); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("mousedown", away);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("mousedown", away); window.removeEventListener("keydown", esc); };
  }, [active, onClose]);

  if (!state.visible) return null;

  const slot = (item: { id: string; icon: string; label: string; hint: string; key?: string; on: boolean; why: string | null }) => {
    const lit = active === item.id;
    return (
      <button
        key={item.id}
        type="button"
        aria-label={item.label}
        aria-pressed={lit}
        aria-disabled={!item.on}
        title={item.on ? (item.key ? `${item.hint} (${item.key})` : item.hint) : (item.why ?? item.hint)}
        onClick={() => { if (item.on) onSlot(item.id); }}
        style={{
          width: 34, height: 34, display: "grid", placeItems: "center", borderRadius: 9, cursor: item.on ? "pointer" : "not-allowed",
          background: lit ? K.on : "none", border: `1px solid ${lit ? K.line : "transparent"}`,
          color: item.on ? (lit ? K.accent : K.dim) : "#3f3f46",
        }}
      >
        <Icon name={item.icon} />
      </button>
    );
  };

  return (
    <div ref={root} style={{ position: "absolute", left: 12, top: 12, bottom: 12, zIndex: 14, display: "flex" }}>
      <div
        role="toolbar"
        aria-label="board controls"
        style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center", background: K.bg, border: `1px solid ${K.line}`, borderRadius: 12, padding: 5, boxShadow: "0 16px 40px rgba(0,0,0,0.5)", height: "fit-content" }}
      >
        {state.items.slice(0, 4).map(slot)}
        <span style={{ width: 20, height: 1, background: K.line, margin: "4px 0" }} />
        {slot(state.items[4])}
        <button
          type="button"
          aria-label={state.run.label}
          aria-disabled={!state.run.on}
          title={state.run.on ? state.run.hint : (state.run.why ?? state.run.hint)}
          onClick={() => { if (state.run.on) onRun(); }}
          style={{ marginTop: 6, width: 34, height: 34, display: "grid", placeItems: "center", borderRadius: 9, border: `1px solid ${state.run.on ? "rgba(167,139,250,0.45)" : K.line}`, background: state.run.on ? "rgba(167,139,250,0.14)" : "none", color: state.run.on ? K.accent : "#3f3f46", cursor: state.run.on ? "pointer" : "not-allowed" }}
        >
          <Icon name="run" size={16} />
        </button>
      </div>

      {active && children ? (
        <div
          role="dialog"
          aria-label={active}
          style={{ marginLeft: 8, width: 380, maxHeight: "min(660px, calc(100vh - 40px))", overflowY: "auto", background: K.bg, border: `1px solid ${K.line}`, borderRadius: 12, padding: 14, boxShadow: "0 18px 50px rgba(0,0,0,0.55)", color: K.text, fontSize: 12.5, height: "fit-content" }}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}
