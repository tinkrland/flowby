/**
 * Chrome: the command bar. a thin skin over nodeui.mjs.
 *
 * the toolbar is a floating pill: one button per wire type, a `+` that opens the command bar, and
 * an Execute button that is absent until a runnable node is selected. the command bar lists every
 * preset with its type signature as coloured chips, so what a node takes and gives is visible
 * before it is added. quick connect is the same list, filtered to what could be wired to the
 * socket you dragged from.
 *
 * dark only. neutrals only, plus the wire hues that nodeui hands back.
 */

import { useEffect, useMemo, useRef, useState } from "react";

import { quickConnect, searchCommands } from "./nodeui.mjs";
import type { CommandRow, Chip } from "./nodeui.mjs";

const K = { bg: "#121214", line: "#1f1f23", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa", hover: "#1a1a1e" };

function ChipView({ chip }: { chip: Chip }) {
  return (
    <span
      title={chip.dtype}
      style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 10, color: K.dim, border: `1px solid ${K.line}`, borderRadius: 6, padding: "1px 6px" }}
    >
      <span style={{ width: 6, height: 6, borderRadius: 3, background: chip.hex }} />
      {chip.label}
    </span>
  );
}

export type BarMode = { kind: "all" } | { kind: "connect"; side: "in" | "out"; dtype: string; role: string | null; x: number; y: number };

export function CommandBar({
  rows, mode, onPick, onClose,
}: {
  rows: CommandRow[];
  mode: BarMode;
  onPick: (row: CommandRow, mode: BarMode) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  const pool = useMemo(
    () => (mode.kind === "connect" ? quickConnect(rows, mode).options : rows),
    [rows, mode],
  );
  const found = useMemo(() => searchCommands(pool, query), [pool, query]);
  useEffect(() => { input.current?.focus(); }, []);
  useEffect(() => { setCursor(0); }, [query, mode]);

  const place: React.CSSProperties =
    mode.kind === "connect"
      ? { position: "fixed", left: Math.min(mode.x, window.innerWidth - 380), top: Math.min(mode.y, window.innerHeight - 360) }
      : { position: "absolute", left: "50%", bottom: 72, transform: "translateX(-50%)" };

  return (
    <div
      role="dialog"
      aria-label={mode.kind === "connect" ? "connect to" : "add a node"}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
        else if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, found.length - 1)); }
        else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
        else if (e.key === "Enter" && found[cursor]) onPick(found[cursor], mode);
      }}
      style={{ ...place, zIndex: 20, width: 360, background: K.bg, border: `1px solid ${K.line}`, borderRadius: 12, boxShadow: "0 18px 50px rgba(0,0,0,0.6)", color: K.text, font: "13px ui-sans-serif, system-ui, sans-serif", overflow: "hidden" }}
    >
      <input
        ref={input}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={mode.kind === "connect" ? `connect ${mode.dtype} ${mode.side === "out" ? "to" : "from"}…` : "type to search for nodes…"}
        style={{ width: "100%", boxSizing: "border-box", background: "none", border: 0, borderBottom: `1px solid ${K.line}`, color: K.text, padding: "12px 14px", outline: "none", fontSize: 13 }}
      />
      <div role="listbox" style={{ maxHeight: 300, overflow: "auto", padding: 4 }}>
        {found.length === 0 && (
          <div style={{ padding: "12px 12px", color: K.mute, fontSize: 12 }}>
            {mode.kind === "connect" && pool.length === 0 ? `nothing takes ${mode.dtype} here` : "no node matches that"}
          </div>
        )}
        {found.map((r, i) => (
          <div
            key={r.id}
            role="option"
            aria-selected={i === cursor}
            onMouseEnter={() => setCursor(i)}
            onClick={() => onPick(r, mode)}
            style={{ padding: "8px 10px", borderRadius: 8, background: i === cursor ? K.hover : "none", cursor: "pointer" }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span>{r.label}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <ChipView chip={r.signature.chips[0]} />
                <span style={{ color: K.mute }}>→</span>
                <ChipView chip={r.signature.chips[1]} />
              </span>
            </div>
            <div style={{ color: K.mute, fontSize: 11, marginTop: 2 }}>
              {r.stage}{r.estimate ? ` · about ${r.estimate} min` : ""}{r.models.length ? ` · ${r.models.join(", ")}` : " · no model"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
