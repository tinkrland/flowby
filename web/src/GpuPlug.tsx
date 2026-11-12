/**
 * GpuPlug: the corner button and the panel under it. a skin over gpuplug.mjs and api.mjs.
 *
 * it draws what python reported and decides nothing about it. the dot's colour, the button's words
 * and every "connected" come from gpuplug.mjs, which only produces them from a state python called
 * `up`. the token lives in this component's form state while it is typed, goes out once in a POST
 * body, and the form is emptied whether the request worked or not.
 *
 * dark only, like the rest of the page. the one hue it adds beyond the page's accent is the state
 * dot, and that is data (green up, red down, grey unchecked), not decoration.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Refused, Unreachable, baseUrl, client } from "./api.mjs";
import type { PlugList, PlugView } from "./api.mjs";
import { EMPTY_FORM, STALE_AFTER_S, ago, body, buttonState, canSubmit, clear, formWords, hints, isStale, rowOf } from "./gpuplug.mjs";

const N = { bg: "#121214", line: "#26262a", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", field: "#0b0b0d", accent: "#a78bfa", bad: "#f87171" };
const TONE: Record<string, string> = { up: "#4ade80", down: "#f87171", idle: "#a1a1aa", off: "#52525b" };

type Form = { label: string; provider: string; endpoint: string; token: string; tunnel: boolean };

export function GpuPlug() {
  const api = useMemo(() => client({ base: baseUrl((import.meta as any).env ?? {}) }), []);
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<PlugList | null>(null);
  const [reachable, setReachable] = useState(true);
  const [form, setForm] = useState<Form>({ ...EMPTY_FORM });
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const [narrow, setNarrow] = useState(typeof window !== "undefined" && window.innerWidth < 560);
  useEffect(() => { const f = () => setNarrow(window.innerWidth < 560); window.addEventListener("resize", f); return () => window.removeEventListener("resize", f); }, []);
  const root = useRef<HTMLDivElement | null>(null);
  // on a phone the panel hangs from the header's real bottom, which moves when the header wraps
  const [top, setTop] = useState(52);
  useEffect(() => { if (open) { const h = root.current?.closest("header"); if (h) setTop(Math.round(h.getBoundingClientRect().bottom) + 6); } }, [open, narrow]);

  const load = useCallback(async () => {
    try {
      setList(await api.plugs());
      setReachable(true);
    } catch (e) {
      if (e instanceof Unreachable) setReachable(false);
      else setProblem(e instanceof Error ? e.message : "something went wrong");
    }
  }, [api]);

  useEffect(() => { void load(); }, [load]);
  // a green that is not refreshed goes stale, and the page re-reads the clock so it can say so
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 15000); return () => clearInterval(t); }, []);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (root.current && !root.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("mousedown", away);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("mousedown", away); window.removeEventListener("keydown", esc); };
  }, [open]);

  const plugs: PlugView[] = list?.plugs ?? [];
  const button = buttonState(plugs, { reachable });
  const providers = list?.providers;
  const found = hints(form, providers);
  const words = formWords(form.provider, providers);
  const providerNote = list?.providers?.[form.provider]?.note;

  async function run<T>(key: string, job: () => Promise<T>): Promise<T | undefined> {
    setBusy(key);
    setProblem(null);
    try {
      return await job();
    } catch (e) {
      if (e instanceof Unreachable) setReachable(false);
      setProblem(e instanceof Refused || e instanceof Unreachable ? e.message : "something went wrong");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function add() {
    if (!canSubmit(form, providers)) return;
    const sent = body(form, providers);
    // the form is emptied before the answer, so a slow or failed request cannot leave a token on screen
    setForm(clear() as Form);
    const made = await run("add", () => api.addPlug(sent));
    if (made) {
      setList((old) => (old ? { ...old, plugs: made.plugs } : old));
      setReachable(true);
      // a plug is added unchecked. checking is a separate, visible act, so "connected" is never a side effect of adding
    }
  }

  async function check(id: string) {
    const done = await run(`check:${id}`, () => api.checkPlug(id));
    if (done) setList((old) => (old ? { ...old, plugs: done.plugs } : old));
  }

  async function remove(id: string) {
    const done = await run(`remove:${id}`, () => api.removePlug(id));
    if (done) setList((old) => (old ? { ...old, plugs: done.plugs } : old));
  }

  return (
    <div ref={root} style={{ position: "relative", marginLeft: 8 }}>
      <button
        onClick={() => { setOpen((o) => !o); if (!open) void load(); }}
        aria-haspopup="dialog"
        aria-expanded={open}
        title={button.title}
        style={{ display: "flex", alignItems: "center", gap: 7, background: "#27272a", color: N.text, border: 0, borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" }}
      >
        <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: TONE[button.tone], boxShadow: button.tone === "up" ? "0 0 0 3px rgba(74,222,128,0.18)" : "none" }} />
        {button.label}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="plug a gpu"
          style={{ ...(narrow ? { position: "fixed", top: top, left: 12, right: 12, width: "auto" } : { position: "absolute", top: "calc(100% + 8px)", right: 0, width: 400 }), maxHeight: "min(640px, calc(100vh - 80px))", overflowY: "auto", background: N.bg, border: `1px solid ${N.line}`, borderRadius: 12, padding: 14, zIndex: 30, boxShadow: "0 18px 50px rgba(0,0,0,0.55)", color: N.text, fontSize: 12.5 }}
        >
          <div style={{ fontSize: 13.5, fontWeight: 600 }}>plug a gpu</div>
          <div style={{ color: N.mute, marginTop: 3, lineHeight: 1.45 }}>
            run models on a gpu you rent. flowby talks to the model server on it, and calls it connected only after that server answers a health check.
          </div>

          {!reachable && (
            <div role="alert" style={{ marginTop: 12, padding: "9px 11px", border: `1px solid #4c2a2a`, background: "#1c1212", color: "#fca5a5", borderRadius: 8, lineHeight: 1.45 }}>
              flowby's server is not running, so nothing can be plugged in from this page. start it and reopen this.
            </div>
          )}

          {plugs.length > 0 && (
            <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "grid", gap: 8 }}>
              {plugs.map((p) => {
                const r = rowOf(p);
                const stale = isStale(p, now);
                const dot = stale ? { hex: "#a3a34a", word: "may have gone" } : r.dot;
                return (
                  <li key={p.id} style={{ border: `1px solid ${N.line}`, borderRadius: 10, padding: "10px 11px", background: "#0e0e10" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: dot.hex, flex: "none" }} />
                      <strong style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.title}</strong>
                      <span style={{ color: stale ? "#d4d46a" : N.mute, marginLeft: "auto", whiteSpace: "nowrap" }}>{dot.word}</span>
                    </div>
                    <div style={{ color: N.mute, marginTop: 4, wordBreak: "break-all" }}>{r.sub}</div>
                    <div style={{ color: N.dim, marginTop: 5, lineHeight: 1.45 }}>{r.detail}</div>
                    {stale && <div style={{ color: "#d4d46a", marginTop: 4 }}>last checked {ago(r.checked, now)}, over {STALE_AFTER_S / 60} min ago. check again to be sure.</div>}
                    {p.state === "up" && !stale && r.checked && <div style={{ color: N.mute, marginTop: 4 }}>checked {ago(r.checked, now)}{r.version ? ` · vllm ${r.version}` : ""}</div>}
                    {r.models.length > 0 && p.state === "up" && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 7 }}>
                        {r.models.map((m: string) => <span key={m} style={{ background: "#1c1c20", color: N.dim, borderRadius: 6, padding: "2px 7px", fontSize: 11.5 }}>{m}</span>)}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 6, marginTop: 9 }}>
                      {r.action && (
                        <button onClick={() => check(p.id)} disabled={busy !== null} style={{ ...small, background: N.accent, color: "#0b0b0d", fontWeight: 600 }}>
                          {busy === `check:${p.id}` ? "asking the server…" : r.action}
                        </button>
                      )}
                      <button onClick={() => remove(p.id)} disabled={busy !== null} style={small}>unplug</button>
                      {r.hasToken && <span style={{ color: N.mute, marginLeft: "auto", alignSelf: "center" }}>token held</span>}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          <form
            onSubmit={(e) => { e.preventDefault(); void add(); }}
            autoComplete="off"
            style={{ marginTop: 14, paddingTop: 12, borderTop: plugs.length ? `1px solid ${N.line}` : "none", display: "grid", gap: 9 }}
          >
            <div style={{ color: N.dim, fontWeight: 600 }}>{plugs.length ? "plug in another" : "connect one"}</div>
            <Field label="name" hint={found.find((h) => h.field === "label" && form.label)} >
              <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="vultr a100" style={input} maxLength={60} />
            </Field>
            <Field label="where it runs">
              <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} style={input}>
                {Object.entries(list?.providers ?? { other: { label: "another provider, or your own machine" } }).map(([k, v]) => <option key={k} value={k}>{(v as any).label}</option>)}
              </select>
              {providerNote && <div style={{ color: N.mute, marginTop: 5, lineHeight: 1.45 }}>{providerNote}</div>}
            </Field>
            <Field label="address" hint={form.endpoint ? found.find((h) => h.field === "endpoint") : undefined}>
              <input value={form.endpoint} onChange={(e) => setForm({ ...form, endpoint: e.target.value })} placeholder={words.endpoint} style={input} spellCheck={false} />
            </Field>
            <Field label={words.tokenLabel} hint={found.find((h) => h.field === "token")}>
              {/* a password field: not shown, not offered for autofill, and emptied the moment it is sent */}
              <input type="password" value={form.token} onChange={(e) => setForm({ ...form, token: e.target.value })} placeholder={words.tokenHint} style={input} autoComplete="new-password" spellCheck={false} />
            </Field>
            {words.tunnel && (
              <label style={{ display: "flex", gap: 8, alignItems: "flex-start", color: N.dim, lineHeight: 1.45 }}>
                <input type="checkbox" checked={form.tunnel} onChange={(e) => setForm({ ...form, tunnel: e.target.checked })} style={{ marginTop: 3 }} />
                <span>this address is reached through a tunnel i set up (a private address is otherwise refused)</span>
              </label>
            )}
            <button type="submit" disabled={!canSubmit(form, providers) || busy !== null} style={{ ...small, padding: "8px 12px", background: canSubmit(form, providers) ? N.accent : "#27272a", color: canSubmit(form, providers) ? "#0b0b0d" : N.mute, fontWeight: 600 }}>
              {busy === "add" ? "plugging in…" : "plug in"}
            </button>
            <div style={{ color: N.mute, lineHeight: 1.45 }}>{words.after}</div>
          </form>

          {problem && <div role="alert" style={{ marginTop: 10, color: N.bad, lineHeight: 1.45 }}>{problem}</div>}
          {list?.auth && words.tunnel && <div style={{ marginTop: 10, color: "#52525b", fontSize: 11.5, lineHeight: 1.45 }}>token: {list.auth}</div>}
        </div>
      )}
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: { say: string }; children: React.ReactNode }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <span style={{ color: N.mute, fontSize: 11.5 }}>{label}</span>
      {children}
      {hint && <span role="note" style={{ color: "#fbbf24", fontSize: 11.5 }}>{hint.say}</span>}
    </label>
  );
}

const input: React.CSSProperties = { width: "100%", boxSizing: "border-box", background: N.field, color: N.text, border: `1px solid ${N.line}`, borderRadius: 7, padding: "7px 9px", font: "inherit" };
const small: React.CSSProperties = { background: "#27272a", color: N.text, border: 0, borderRadius: 7, padding: "5px 10px", cursor: "pointer", font: "inherit" };
