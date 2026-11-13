/**
 * FocusView: the selection as a form, with no canvas in sight.
 *
 * this is fuser's focus mode, sized from a real frame (docs/frames/recipe-focus-mode.jpg): a top bar
 * with the thing's name and an X, a narrow left column holding one sentence of what it does, then one
 * field per input, one full-width button, the price under the button, and the output filling the rest.
 * **exactly one action.** no re-roll beside generate, no settings drawer. that restraint is the whole
 * design: it is what lets someone use a chain without meeting the graph.
 *
 * the shape is borrowed; the colours are not. fuser's focus view is pale, flowby is dark only.
 *
 * what this file does not do: save. there is no route that writes a node's params (`/api/value` writes
 * a preset instance's slider, nothing more), so an edit here lives on the page and the view says so
 * rather than pretending a keystroke reached python.
 */

import { useEffect, useMemo, useState } from "react";

import type { pill } from "./selection.mjs";

const K = { bg: "#0d0d0f", slab: "#131316", line: "#26262b", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa", field: "#101013" };

export type FocusViewProps = {
  model: ReturnType<typeof pill>;
  /** what the page can say about running. the worker is not on this page, so this is usually a refusal. */
  run: { label: string; enabled: boolean; because: string };
  onRun: () => string;
  onClose: () => void;
};

export function FocusView({ model, run, onRun, onClose }: FocusViewProps) {
  const initial = useMemo(() => Object.fromEntries(model.fields.map((f) => [f.name, f.value])), [model]);
  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => setValues(initial), [initial]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const edited = model.fields.some((f) => values[f.name] !== f.value);

  return (
    <div role="dialog" aria-modal="true" aria-label={`${model.title}, focus view`} style={{ position: "absolute", inset: 0, zIndex: 30, display: "flex", flexDirection: "column", background: K.bg }}>
      <header style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderBottom: `1px solid ${K.line}`, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 13, color: K.text }}>{model.title}</strong>
        <span style={{ fontSize: 11, color: K.mute }}>{model.count === 1 ? "one node, opened as a form" : `a chain of ${model.count} nodes`}</span>
        <button onClick={onClose} aria-label="close focus view" title="close" style={{ marginLeft: "auto", width: 28, height: 28, background: "none", border: `1px solid ${K.line}`, borderRadius: 8, color: K.dim, cursor: "pointer", fontSize: 14 }}>×</button>
      </header>

      <div style={{ flex: 1, minHeight: 0, display: "flex", flexWrap: "wrap" }}>
        {/* the left column: a sentence, its inputs, one button, the price */}
        <aside style={{ flex: "0 0 320px", minWidth: 260, maxWidth: "100%", borderRight: `1px solid ${K.line}`, padding: 16, display: "flex", flexDirection: "column", gap: 14, overflowY: "auto" }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: 0.4, textTransform: "uppercase", color: K.mute, marginBottom: 6 }}>Description</div>
            <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: K.dim }}>
              {model.count === 1
                ? `this runs ${model.chosen[0]?.op ?? "one step"} and hands on what it makes. set what it needs below, then run it.`
                : `these ${model.count} nodes run left to right as one chain. their inputs are read from the graph; nothing else has to be set.`}
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, letterSpacing: 0.4, textTransform: "uppercase", color: K.mute }}>Inputs</span>
            <button
              onClick={() => { setValues(initial); setStatus(null); }}
              disabled={!edited}
              style={{ background: "none", border: 0, color: edited ? K.dim : "#3f3f46", fontSize: 11, cursor: edited ? "pointer" : "default" }}
            >
              reset inputs
            </button>
          </div>

          {model.fields.length === 0 && (
            <p style={{ margin: 0, fontSize: 12, color: K.mute }}>
              nothing to set: {model.count === 1 ? "this node takes what it is wired to" : "a chain is read from the graph, not typed here"}.
            </p>
          )}

          {model.fields.map((f) => (
            <label key={f.name} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <span style={{ fontSize: 11, color: K.mute }}>{f.name}</span>
              {f.kind === "switch" ? (
                <button
                  role="switch"
                  aria-checked={Boolean(values[f.name])}
                  onClick={() => setValues((v) => ({ ...v, [f.name]: !v[f.name] }))}
                  style={{ alignSelf: "flex-start", display: "inline-flex", alignItems: "center", gap: 7, background: K.field, border: `1px solid ${K.line}`, borderRadius: 999, padding: "5px 10px", color: K.text, fontSize: 11.5, cursor: "pointer" }}
                >
                  <span aria-hidden style={{ width: 8, height: 8, borderRadius: 4, background: values[f.name] ? K.accent : "#3f3f46" }} />
                  {values[f.name] ? "on" : "off"}
                </button>
              ) : f.kind === "number" ? (
                <input
                  type="number"
                  value={Number(values[f.name] ?? 0)}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: Number(e.target.value) }))}
                  style={{ background: K.field, border: `1px solid ${K.line}`, borderRadius: 8, color: K.text, padding: "7px 9px", fontSize: 12, fontVariantNumeric: "tabular-nums" }}
                />
              ) : f.kind === "text" ? (
                <textarea
                  rows={String(values[f.name] ?? "").length > 60 ? 3 : 1}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                  style={{ background: K.field, border: `1px solid ${K.line}`, borderRadius: 8, color: K.text, padding: "7px 9px", fontSize: 12, lineHeight: 1.5, resize: "vertical", fontFamily: "inherit" }}
                />
              ) : (
                <span title="shown, not editable" style={{ background: K.field, border: `1px dashed ${K.line}`, borderRadius: 8, color: K.mute, padding: "7px 9px", fontSize: 12 }}>
                  {f.kind === "empty" ? "none" : "set elsewhere"}
                </span>
              )}
            </label>
          ))}

          <button
            onClick={() => setStatus(onRun())}
            aria-disabled={!run.enabled}
            title={run.enabled ? run.label : run.because}
            style={{ marginTop: "auto", width: "100%", padding: "10px 12px", borderRadius: 10, border: `1px solid ${run.enabled ? "#4c3f79" : K.line}`, background: run.enabled ? "#2a2340" : "#17171b", color: run.enabled ? K.text : K.mute, fontSize: 12.5, cursor: run.enabled ? "pointer" : "not-allowed" }}
          >
            {run.label}
          </button>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: K.mute }}>
            <span title={model.cost.hint}>{model.cost.text}</span>
            {edited && <span title="no route writes a node's params yet">edits stay on this page</span>}
          </div>
        </aside>

        {/* the output, which is most of the screen because that is what you came for */}
        <main style={{ flex: "1 1 320px", minWidth: 0, display: "flex", flexDirection: "column", padding: 16, gap: 12 }}>
          <div style={{ flex: 1, minHeight: 180, borderRadius: 12, border: `1px solid ${K.line}`, background: K.slab, display: "grid", placeItems: "center", color: K.mute, fontSize: 12, textAlign: "center", padding: 20 }}>
            <div>
              <div style={{ marginBottom: 6, color: K.dim }}>no output yet</div>
              <div>run it, and what this {model.count === 1 ? "node" : "chain"} makes appears here</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 11, color: K.mute, flexWrap: "wrap" }}>
            <span>Output</span>
            <button aria-label="previous run" disabled style={{ background: "none", border: `1px solid ${K.line}`, borderRadius: 6, color: "#3f3f46", padding: "1px 7px" }}>‹</button>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>Run 1/1</span>
            <button aria-label="next run" disabled style={{ background: "none", border: `1px solid ${K.line}`, borderRadius: 6, color: "#3f3f46", padding: "1px 7px" }}>›</button>
            <span style={{ marginLeft: "auto" }}>idle</span>
          </div>
          <div aria-hidden style={{ height: 3, borderRadius: 2, background: "#1c1c21", overflow: "hidden" }}>
            <div style={{ width: "0%", height: "100%", background: K.accent }} />
          </div>
          {status && <div role="status" style={{ fontSize: 11.5, color: K.dim }}>{status}</div>}
        </main>
      </div>
    </div>
  );
}
