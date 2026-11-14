/**
 * KitsMenu: the preset kits button and its panel. a skin over kitsmenu.mjs and api.mjs.
 * it draws what python listed. a style that is only a name on a list is drawn dim, with its true
 * state in words and no button, so it cannot be mistaken for something that runs.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Unreachable, baseUrl, client } from "./api.mjs";
import { kitView, kitsButton } from "./kitsmenu.mjs";
import type { KitData } from "./kitsmenu.mjs";
import { KitRowView } from "./KitRow";

const N = { bg: "#121214", line: "#26262a", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa" };
const TONE: Record<string, string> = { up: "#4ade80", idle: "#a1a1aa", off: "#52525b" };

export function KitsMenu({ embedded = false, onPlaced }: { embedded?: boolean; onPlaced?: (answer: any) => void } = {}) {
  const api = useMemo(() => client({ base: baseUrl((import.meta as any).env ?? {}) }), []);
  // embedded means the rail owns the open state: the panel is the slot's content, not a popover
  const [open, setOpen] = useState(embedded);
  const [kits, setKits] = useState<KitData[] | null>(null);
  const [reachable, setReachable] = useState(true);
  const [narrow, setNarrow] = useState(typeof window !== "undefined" && window.innerWidth < 560);
  const root = useRef<HTMLDivElement | null>(null);
  // on a phone the panel hangs from the header's real bottom, which moves when the header wraps
  const [top, setTop] = useState(52);
  useEffect(() => { if (open) { const h = root.current?.closest("header"); if (h) setTop(Math.round(h.getBoundingClientRect().bottom) + 6); } }, [open, narrow]);
  useEffect(() => { const f = () => setNarrow(window.innerWidth < 560); window.addEventListener("resize", f); return () => window.removeEventListener("resize", f); }, []);

  const load = useCallback(async () => {
    try { const r = await api.kits(); setKits(r.kits ?? []); setReachable(true); }
    catch (e) { if (e instanceof Unreachable) setReachable(false); }
  }, [api]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!open || embedded) return;
    const away = (e: MouseEvent) => { if (root.current && !root.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("mousedown", away);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("mousedown", away); window.removeEventListener("keydown", esc); };
  }, [open]);

  // placing is the one action a worded member offers. it is not a run: python puts a text node and the
  // preset that reads it on the board, and nothing is generated until a model is plugged in.
  const [placing, setPlacing] = useState<string | null>(null);
  const place = useCallback(async (look: string) => {
    setPlacing(look);
    try {
      const answer = await api.placeLook(look);
      onPlaced?.(answer);
    } catch (e) {
      onPlaced?.({ refused: e instanceof Error ? e.message : String(e) });
    } finally { setPlacing(null); }
  }, [api, onPlaced]);

  const button = kitsButton(kits, { reachable });
  const views = (kits ?? []).map(kitView);

  return (
    <div ref={root} style={embedded ? undefined : { position: narrow ? "static" : "relative" }}>
      {!embedded && <button
        onClick={() => { setOpen((o) => !o); if (!open) void load(); }}
        aria-haspopup="dialog"
        aria-expanded={open}
        title={button.title}
        style={{ display: "flex", alignItems: "center", gap: 7, background: "#27272a", color: N.text, border: 0, borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" }}
      >
        <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: TONE[button.tone] }} />
        {button.label}
      </button>}

      {open && (
        <div
          role="dialog"
          aria-label="preset kits"
          style={embedded
            ? { background: N.bg, color: N.text, fontSize: 12.5 }
            : { ...(narrow ? { position: "fixed", top: top, left: 12, right: 12, width: "auto" } : { position: "absolute", top: "calc(100% + 8px)", right: 0, width: 380 }), maxHeight: "min(640px, calc(100vh - 80px))", overflowY: "auto", background: N.bg, border: `1px solid ${N.line}`, borderRadius: 12, padding: 14, zIndex: 30, boxShadow: "0 18px 50px rgba(0,0,0,0.55)", color: N.text, fontSize: 12.5 }}
        >
          {!embedded && <div style={{ fontSize: 13.5, fontWeight: 600 }}>preset kits</div>}
          {/* the rail panel's own sentence already says this, and saying it twice in one panel reads as a bug */}
          {!embedded && (
            <div style={{ color: N.mute, marginTop: 3, lineHeight: 1.45 }}>
              families of styles. a style is listed until its images are gathered and it is trained, and only a trained one can be used.
            </div>
          )}
          {!reachable && <div role="alert" style={{ marginTop: 12, color: "#fca5a5", lineHeight: 1.45 }}>flowby's server is not running, so the kits cannot be read.</div>}
          {views.map((v) => (
            <section key={v.id} style={{ marginTop: 14 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{v.label}</span>
                <span style={{ color: N.mute, marginLeft: "auto" }}>{v.summary}</span>
              </div>
              <div style={{ color: N.mute, marginTop: 2, lineHeight: 1.4 }}>{v.blurb}</div>
              <ul style={{ listStyle: "none", margin: "8px 0 0", padding: 0, display: "grid", gap: 6 }}>
                {v.rows.map((r) => <KitRowView key={r.id} r={r} placing={placing} onPlace={place} />)}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
