/**
 * Panel: the "new node" panel. a thin skin over panel.mjs, which holds every decision.
 *
 * what lives here is only what needs a DOM: reading files the browser hands over, opening a zip,
 * and making the requests. what a file is, whether an import is affordable, and what the token may
 * touch are all decided in panel.mjs and intake.mjs, where node tests can reach them.
 *
 * dark only, like the canvas. no theme prop, no media query.
 *
 * the figma token is typed into a password field, held in the reducer's memory, handed to the
 * client closure, and forgotten when the panel closes. it is never rendered back, never put in a
 * url, and never written to storage.
 */

import { unzipSync } from "fflate";
import { useCallback, useReducer, useRef, useState } from "react";

import * as intake from "./intake.mjs";
import * as panel from "./panel.mjs";
import type { QueueItem, ViewQueueItem } from "./panel.mjs";

export type PlacedElement = {
  kind: string;
  label: string;
  asset: string;
  bytes: number;
  source: Record<string, unknown>;
  warning?: string | null;
};

type Props = {
  /** called with elements ready to put on the board. the board decides where. */
  onPlace: (elements: PlacedElement[]) => void;
  onClose: () => void;
};

const C = {
  bg: "#0b0b0d", card: "#121214", line: "#1c1c1f", text: "#e4e4e7",
  mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa", bad: "#f87171", warn: "#fbbf24",
};

const box = { background: C.card, border: `1px solid ${C.line}`, borderRadius: 10 } as const;
const btn = (on = true) => ({
  background: on ? C.accent : "#27272a", color: on ? "#0b0b0d" : C.mute, border: 0,
  borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 600,
  cursor: on ? "pointer" : "not-allowed",
}) as const;

const quiet = { background: "none", color: C.mute, border: 0, borderRadius: 8, padding: "8px 14px", fontSize: 13, cursor: "pointer" } as const;

async function readFiles(list: FileList | File[]) {
  return Promise.all(
    [...list].map(async (f) => ({ name: f.name, bytes: new Uint8Array(await f.arrayBuffer()) })),
  );
}

export function Panel({ onPlace, onClose }: Props) {
  const [state, dispatch] = useReducer(panel.reduce, undefined, () => panel.reduce(panel.initial(), { type: "open" }));
  const view = panel.view(state);
  const [busy, setBusy] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const accept = useCallback(async (list: FileList | File[]) => {
    dispatch({ type: "files", files: await readFiles(list) });
  }, []);

  const unpack = async (id: string) => {
    const item = state.queue.find((q) => q.id === id);
    if (!item) return;
    try {
      const { files, skipped } = intake.unpackZip(item.bytes, unzipSync);
      dispatch({ type: "unpacked", id, files });
      if (skipped.length) dispatch({ type: "files", files: [] });
    } catch (e) {
      dispatch({ type: "unqueue", id });
      dispatch({ type: "figma-error", error: (e as Error).message });
    }
  };

  const placeUploads = async () => {
    setBusy("placing");
    const ready = state.queue.filter((q) => q.via !== "unpack" && q.via !== "refuse");
    const elements: PlacedElement[] = [];
    const failed: { name: string; reason: string }[] = [];
    for (const q of ready) {
      try { elements.push(await intake.toElement({ name: q.name, bytes: q.bytes })); }
      catch (e) { failed.push({ name: q.name, reason: (e as Error).message }); }
    }
    dispatch({ type: "placed", ids: ready.map((q) => q.id), elements, failed });
    if (elements.length) onPlace(elements);
    setBusy(null);
  };

  // --- figma ---
  const readLink = async () => {
    setBusy("reading the link");
    try {
      const parsed = intake.parseFigma(state.figma.link);
      dispatch({ type: "figma-parsed", parsed });
    } catch (e) { dispatch({ type: "figma-error", error: (e as Error).message }); }
    setBusy(null);
  };

  const listFrames = async () => {
    setBusy("asking figma for the frames");
    try {
      const client = panel.figmaClient({ token: state.figma.token });
      const { parsed } = state.figma;
      if (!parsed) throw new intake.IntakeRefused("paste a figma link first");
      const response = parsed.nodeId ? await client.nodes(parsed.fileKey, [parsed.nodeId]) : await client.file(parsed.fileKey);
      const { frames, missing } = panel.framesFromResponse(response, parsed.nodeId ? [parsed.nodeId] : null);
      if (!frames.length) throw new intake.IntakeRefused("figma returned that file, but it has no frames to import");
      dispatch({ type: "figma-frames", frames, missing });
    } catch (e) { dispatch({ type: "figma-error", error: (e as Error).message }); }
    setBusy(null);
  };

  const importFrames = async () => {
    setBusy("importing");
    try {
      const client = panel.figmaClient({ token: state.figma.token });
      if (!state.figma.parsed) throw new intake.IntakeRefused("paste a figma link first");
      const out = await panel.importPicked({
        client, parsed: state.figma.parsed, frames: state.figma.frames, picked: state.figma.picked, seat: state.figma.seat,
        // exported images are signed storage links: fetched with no figma token attached
        download: async (url: string) => {
          const res = await fetch(url);
          if (!res.ok) throw new Error(`${res.status}`);
          return new Uint8Array(await res.arrayBuffer());
        },
      });
      dispatch({ type: "placed", ids: [], elements: out.elements, failed: out.failed });
      if (out.elements.length) onPlace(out.elements);
      dispatch({ type: "figma-reset" });
    } catch (e) { dispatch({ type: "figma-error", error: (e as Error).message }); }
    setBusy(null);
  };

  const close = () => { dispatch({ type: "close" }); onClose(); };
  const f = view.figma;

  return (
    <aside
      role="dialog"
      aria-label="new node"
      style={{ ...box, width: 380, maxHeight: "100%", overflow: "auto", background: C.bg, color: C.text, padding: 16, fontSize: 13 }}
    >
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <strong>new node</strong>
        <button onClick={close} aria-label="close" style={{ background: "none", border: 0, color: C.mute, cursor: "pointer", fontSize: 16 }}>×</button>
      </header>

      <div role="tablist" style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        {(["upload", "figma"] as const).map((d) => (
          <button
            key={d} role="tab" aria-selected={view.door === d} onClick={() => dispatch({ type: "door", door: d })}
            style={{ ...btn(view.door === d), flex: 1 }}
          >
            {d === "upload" ? "upload files" : "import from figma"}
          </button>
        ))}
      </div>

      {view.door === "upload" && (
        <section>
          <div
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); void accept(e.dataTransfer.files); }}
            onClick={() => input.current?.click()}
            style={{ ...box, borderStyle: "dashed", borderColor: over ? C.accent : "#3f3f46", padding: 24, textAlign: "center", color: C.dim, cursor: "pointer" }}
          >
            drop files here, or click to choose
            <div style={{ color: C.mute, fontSize: 11, marginTop: 6 }}>png, jpeg, webp, gif, avif, svg, mp4, webm, glb, or a zip of images</div>
          </div>
          <input ref={input} type="file" multiple hidden onChange={(e) => e.target.files && void accept(e.target.files)} />

          {view.queue.map((q: ViewQueueItem) => (
            <div key={q.id} style={{ ...box, padding: "8px 10px", marginTop: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{q.name}</span>
                <span style={{ color: C.mute }}>{q.type}, {(q.size / 1024).toFixed(0)} KB</span>
              </div>
              {q.warning && <div style={{ color: C.warn, fontSize: 11, marginTop: 4 }}>{q.warning}</div>}
              {q.note && <div style={{ color: C.mute, fontSize: 11, marginTop: 4 }}>{q.note}</div>}
              <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                {q.via === "unpack" && <button onClick={() => void unpack(q.id)} style={btn()}>open zip</button>}
                <button onClick={() => dispatch({ type: "unqueue", id: q.id })} style={quiet}>remove</button>
              </div>
            </div>
          ))}

          <button disabled={!view.canPlace || !!busy} onClick={() => void placeUploads()} style={{ ...btn(view.canPlace && !busy), width: "100%", marginTop: 12 }}>
            {busy === "placing" ? "placing…" : `place ${view.queue.filter((q) => q.via !== "unpack").length} on the board`}
          </button>
        </section>
      )}

      {view.door === "figma" && (
        <section style={{ display: "grid", gap: 10 }}>
          {f.step === "link" && (
            <>
              <label style={{ color: C.dim }}>figma link
                <input
                  value={state.figma.link} placeholder="https://www.figma.com/design/…?node-id=…"
                  onChange={(e) => dispatch({ type: "figma-link", link: e.target.value })}
                  style={{ width: "100%", boxSizing: "border-box", marginTop: 4, background: C.card, color: C.text, border: `1px solid ${C.line}`, borderRadius: 8, padding: 8 }}
                />
              </label>
              <button disabled={!state.figma.link || !!busy} onClick={() => void readLink()} style={btn(!!state.figma.link && !busy)}>continue</button>
            </>
          )}

          {f.step === "token" && (
            <>
              <label style={{ color: C.dim }}>figma personal access token
                <input
                  type="password" autoComplete="off" spellCheck={false} value={state.figma.token}
                  onChange={(e) => dispatch({ type: "figma-token", token: e.target.value })}
                  style={{ width: "100%", boxSizing: "border-box", marginTop: 4, background: C.card, color: C.text, border: `1px solid ${C.line}`, borderRadius: 8, padding: 8 }}
                />
              </label>
              <div style={{ color: C.mute, fontSize: 11 }}>
                kept in memory while this panel is open and sent only to api.figma.com. closing the panel forgets it. needs the file_content:read scope.
              </div>
              <label style={{ color: C.dim }}>your seat
                <select
                  value={state.figma.seat} onChange={(e) => dispatch({ type: "figma-seat", seat: e.target.value })}
                  style={{ width: "100%", marginTop: 4, background: C.card, color: C.text, border: `1px solid ${C.line}`, borderRadius: 8, padding: 8 }}
                >
                  <option value="view">view (20 requests a month)</option>
                  <option value="collab">collab (20 requests a month)</option>
                  <option value="dev">dev (per minute)</option>
                  <option value="full">full (per minute)</option>
                </select>
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => dispatch({ type: "figma-reset" })} style={quiet}>back</button>
                <button disabled={!f.hasToken || !!busy} onClick={() => void listFrames()} style={{ ...btn(f.hasToken && !busy), flex: 1 }}>
                  {busy ? `${busy}…` : "list frames"}
                </button>
              </div>
            </>
          )}

          {f.step === "pick" && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", color: C.dim }}>
                <span>{f.frames.length} frames</span>
                <button onClick={() => dispatch({ type: "figma-pick-all" })} style={{ background: "none", border: 0, color: C.accent, cursor: "pointer" }}>pick all</button>
              </div>
              <div style={{ maxHeight: 220, overflow: "auto", display: "grid", gap: 4 }}>
                {f.frames.map((fr: { id: string; name: string; width: number | null; height: number | null; section: string | null }) => (
                  <label key={fr.id} style={{ ...box, padding: "6px 10px", display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
                    <input type="checkbox" checked={f.picked.includes(fr.id)} onChange={() => dispatch({ type: "figma-pick", id: fr.id })} />
                    <span style={{ flex: 1 }}>{fr.name}{fr.section && <span style={{ color: C.mute }}> in {fr.section}</span>}</span>
                    <span style={{ color: C.mute, fontSize: 11 }}>{fr.width && fr.height ? `${Math.round(fr.width)}×${Math.round(fr.height)}` : ""}</span>
                  </label>
                ))}
              </div>
              {f.missing.length > 0 && <div style={{ color: C.warn, fontSize: 11 }}>figma did not return: {f.missing.join(", ")}</div>}
              {f.cost && <div style={{ color: f.cost.fits ? C.dim : C.bad, fontSize: 12 }}>{f.cost.note}</div>}
              <button disabled={!view.canImport || !!busy} onClick={() => void importFrames()} style={btn(view.canImport && !busy)}>
                {busy ? `${busy}…` : `import ${f.picked.length} frame${f.picked.length === 1 ? "" : "s"}`}
              </button>
              <div style={{ color: C.mute, fontSize: 11 }}>images are copied into flowby now. figma's own links expire after 30 days.</div>
            </>
          )}

          {f.error && <div role="alert" style={{ color: C.bad, fontSize: 12 }}>{f.error}</div>}
        </section>
      )}

      {view.refused.length > 0 && (
        <section aria-label="not taken" style={{ marginTop: 14 }}>
          <div style={{ color: C.dim, marginBottom: 4 }}>not taken</div>
          {view.refused.map((r: { name: string; reason: string }, i: number) => (
            <div key={i} style={{ display: "flex", gap: 8, color: C.bad, fontSize: 12, marginTop: 4 }}>
              <span style={{ flex: 1 }}><strong>{r.name}</strong>: {r.reason}</span>
              <button onClick={() => dispatch({ type: "dismiss", index: i })} aria-label={`dismiss ${r.name}`} style={{ background: "none", border: 0, color: C.mute, cursor: "pointer" }}>×</button>
            </div>
          ))}
        </section>
      )}
    </aside>
  );
}
