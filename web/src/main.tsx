/**
 * main.tsx: the dev harness, and the only file that knows the app exists.
 *
 * it fetches the graph `bin/flowby --json graph` wrote and draws it. everything the canvas shows is
 * therefore python's output, not a fixture: if the graph command breaks, this page shows nothing
 * and says so.
 *
 * state: designed. it bundles; nobody has panned it.
 */

import { unzipSync } from "fflate";
import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import { NodeCanvas } from "./NodeCanvas";
import { FocusView } from "./FocusView";
import { SelectionPill } from "./SelectionPill";
import { GpuPlug } from "./GpuPlug";
import { KitsMenu } from "./KitsMenu";
import { Viewer } from "./Viewer";
import { isNarrow, viewerRows } from "./viewer.mjs";
import { Panel, type PlacedElement } from "./Panel";
import { CommandBar, Toolbar, type BarMode } from "./Chrome";
import * as gesture from "./gesture.mjs";
import * as intake from "./intake.mjs";
import { commandRows, executeState, isTunable } from "./nodeui.mjs";
import { pill as pillOf } from "./selection.mjs";

type GraphDocument = {
  title: string;
  pipeline: { nodes: any[]; wires: any[] };
};

/** the board is an editor above 760px and a viewer below it. fuser draws the same line at tablet. */
function useNarrow() {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && isNarrow(window.innerWidth));
  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${760 - 1}px)`);
    const onChange = () => setNarrow(isNarrow(window.innerWidth));
    query.addEventListener("change", onChange);
    window.addEventListener("resize", onChange);
    return () => { query.removeEventListener("change", onChange); window.removeEventListener("resize", onChange); };
  }, []);
  return narrow;
}

function App() {
  const [doc, setDoc] = useState<GraphDocument | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [placed, setPlaced] = useState<PlacedElement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [menu, setMenu] = useState<any[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [bar, setBar] = useState<BarMode | null>(null);
  const narrow = useNarrow();
  const [ran, setRan] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [locked, setLocked] = useState<string[]>([]);
  const [more, setMore] = useState(false);
  const [focus, setFocus] = useState(false);
  const [zoom, setZoom] = useState(1);
  const depth = useRef(0);
  const board = useRef<{ duplicate: (ids: string[]) => string[]; remove: (ids: string[]) => void } | null>(null);

  // what arrives by drop or paste goes through the same classification as the panel. a file that
  // cannot be taken is reported by name, and nothing is dropped without a word.
  const take = useCallback(async (files: { name: string; bytes: Uint8Array }[]) => {
    const { placed: ok, refused } = gesture.takeFiles(files);
    const elements: PlacedElement[] = [];
    for (const f of ok) {
      if (f.needs === "unpack") {
        try {
          const { files: inner } = intake.unpackZip(f.bytes, unzipSync);
          for (const i of inner) { try { elements.push(await intake.toElement(i)); } catch { /* listed below */ } }
        } catch (e) { refused.push({ name: f.name, reason: (e as Error).message }); }
        continue;
      }
      try { elements.push(await intake.toElement(f)); } catch (e) { refused.push({ name: f.name, reason: (e as Error).message }); }
    }
    if (elements.length) setPlaced((all) => [...all, ...elements]);
    setNote(
      [elements.length ? `added ${elements.length} node${elements.length === 1 ? "" : "s"}` : "",
        ...refused.map((r) => `${r.name}: ${r.reason}`)].filter(Boolean).join(" · ") || null,
    );
  }, []);

  useEffect(() => {
    const onPaste = async (e: ClipboardEvent) => {
      const files = [...(e.clipboardData?.files ?? [])];
      const verdict = gesture.readPaste({ files, hasText: Boolean(e.clipboardData?.getData("text")), target: e.target as HTMLElement });
      if (verdict.silent) return;
      e.preventDefault();
      const now = new Date();
      await take(await Promise.all(verdict.take.map(async (f: File, i: number) => ({
        name: gesture.nameForPaste(f, i, now), bytes: new Uint8Array(await f.arrayBuffer()),
      }))));
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [take]);

  useEffect(() => {
    fetch("/presets.json").then((r) => (r.ok ? r.json() : null)).then((j) => setMenu(j ? (Array.isArray(j) ? j : (Object.values(j).find(Array.isArray) as any[])) : null)).catch(() => setMenu(null));
  }, []);

  // shift+A or cmd/ctrl+K opens the command bar, as in fuser, unless the user is typing somewhere
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (gesture.typing(e.target as HTMLElement)) return;
      if ((e.shiftKey && e.key.toLowerCase() === "a") || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) {
        e.preventDefault(); setBar({ kind: "all" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    fetch("/graph.json")
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json() as Promise<GraphDocument>;
      })
      .then(setDoc)
      .catch((problem: Error) => setError(`run npm run graph. ${problem.message}`));
  }, []);

  // what the pill says about the current selection, decided by selection.mjs and not by this file
  const pill = pillOf(selected, doc ? doc.pipeline.nodes : [], { locked, tunable: isTunable });

  const act = (name: string) => {
    if (!pill.count) return;
    if (name === "focus") { setFocus(true); return; }
    if (name === "lock") {
      const all = pill.chosen.every((n) => locked.includes(n.id));
      const ids = pill.chosen.map((n) => n.id);
      setLocked((held) => (all ? held.filter((id) => !ids.includes(id)) : [...new Set([...held, ...ids])]));
      setNote(all ? `unlocked ${ids.length} node${ids.length === 1 ? "" : "s"}` : `locked ${ids.length} node${ids.length === 1 ? "" : "s"}: they will not move`);
      return;
    }
    if (name === "duplicate") {
      const ids = pill.chosen.map((n) => n.id);
      const made = board.current?.duplicate(ids) ?? [];
      setSelected(made);
      setNote(`copied ${made.length} node${made.length === 1 ? "" : "s"} on the board. python does not know about the copies yet`);
      return;
    }
    if (name === "delete") {
      const ids = pill.chosen.map((n) => n.id);
      board.current?.remove(ids);
      setSelected([]);
      setLocked((held) => held.filter((id) => !ids.includes(id)));
      setNote(`took ${ids.length} node${ids.length === 1 ? "" : "s"} off the board. python still has them until the board is reloaded`);
    }
  };

  if (error) return <p style={{ padding: 16, color: "#f87171" }}>{error}</p>;
  if (!doc) return <p style={{ padding: 16, color: "#71717a" }}>reading the graph…</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          display: "flex",
          flexWrap: "wrap",          // on a phone the buttons drop to a second line instead of squeezing the title
          gap: "8px 12px",
          alignItems: "baseline",
          padding: "10px 16px",
          borderBottom: "1px solid #1c1c1f",
        }}
      >
        <strong>{doc.title}</strong>
        <span style={{ color: "#71717a", fontSize: 12 }}>
          {doc.pipeline.nodes.length} nodes, {doc.pipeline.wires.length} wires
          {placed.length > 0 && `, ${placed.length} added by hand`}
        </span>
        <span title="camera zoom" style={{ marginLeft: "auto", color: "#71717a", fontSize: 12, fontVariantNumeric: "tabular-nums" }}>
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setPanelOpen((open) => !open)}
          style={{ background: "#27272a", color: "#e4e4e7", border: 0, borderRadius: 8, padding: "6px 12px", cursor: "pointer", whiteSpace: "nowrap" }}
        >
          new node
        </button>
        {/* the far right corner of the page: plug in a gpu you rent. it sits in the header, above
            the new-node panel, so the two can both be open without covering each other */}
        <KitsMenu />
        <GpuPlug />
      </header>
      <div
        style={{ flex: 1, minHeight: 0, position: "relative" }}
        onDragEnter={(e) => { if (gesture.carriesFiles(e.dataTransfer.types)) { depth.current += 1; setDragging(true); } }}
        onDragOver={(e) => { if (gesture.carriesFiles(e.dataTransfer.types)) e.preventDefault(); }}
        onDragLeave={() => { depth.current = Math.max(0, depth.current - 1); if (depth.current === 0) setDragging(false); }}
        onDrop={async (e) => {
          if (!gesture.carriesFiles(e.dataTransfer.types)) return;
          e.preventDefault(); depth.current = 0; setDragging(false);
          const files = await Promise.all([...e.dataTransfer.files].map(async (f) => ({ name: f.name, bytes: new Uint8Array(await f.arrayBuffer()) })));
          await take(files);
        }}
      >
        {narrow ? (
          <Viewer rows={viewerRows(doc.pipeline.nodes)} title={doc.title} />
        ) : (
          <NodeCanvas
            pipeline={doc.pipeline}
            onSelect={(ids) => { setSelected(ids); if (!ids.length) setMore(false); }}
            onQuickConnect={(drop) => setBar({ kind: "connect", ...drop })}
            locked={locked}
            onZoom={setZoom}
            board={board}
          />
        )}
        {!narrow && (
          <Toolbar
            execute={executeState(selected, Object.fromEntries(doc.pipeline.nodes.map((n: any) => [n.id, n])))}
            onExecute={() => setRan(`would run ${selected.length} node${selected.length === 1 ? "" : "s"}: the worker is not connected to this page`)}
            onOpenBar={() => setBar({ kind: "all" })}
            onAddType={() => setPanelOpen(true)}
          />
        )}
        {pill.visible && (
          <SelectionPill
            model={pill}
            onAction={act}
            moreOpen={more}
            onMore={setMore}
            onMorePick={(name) => {
              if (name === "copy") {
                const ids = pill.chosen.map((n) => n.id);
                navigator.clipboard?.writeText(ids.join("\n")).then(
                  () => setNote(`copied ${ids.length} id${ids.length === 1 ? "" : "s"}`),
                  () => setNote("this browser would not let the page copy"),
                );
              }
              setMore(false);
            }}
          />
        )}
        {focus && pill.visible && (
          <FocusView
            model={pill}
            run={{ label: "run", enabled: false, because: "the worker is not connected to this page" }}
            onRun={() => `would run ${pill.count} node${pill.count === 1 ? "" : "s"}: the worker is not connected to this page`}
            onClose={() => setFocus(false)}
          />
        )}
        {bar && menu && (
          <CommandBar
            rows={commandRows(menu)}
            mode={bar}
            onClose={() => setBar(null)}
            onPick={(row) => { setNote(`${row.label}: picked from the command bar. placing it on the board is the python bridge, which is not built yet`); setBar(null); }}
          />
        )}
        {dragging && (
          <div
            aria-hidden
            style={{ position: "absolute", inset: 8, border: "2px dashed #a78bfa", borderRadius: 14, background: "rgba(167,139,250,0.07)", pointerEvents: "none", zIndex: 9 }}
          >
            {/* a pill at the top, so the label never lands on a node the way a centred one did */}
            <span style={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", background: "#121214", color: "#c4b5fd", border: "1px solid #3b2f63", borderRadius: 999, padding: "5px 14px", fontSize: 13 }}>
              {gesture.dragState({ types: ["Files"] }).verb}
            </span>
          </div>
        )}
        {ran && <div role="status" style={{ position: "absolute", left: "50%", bottom: 118, transform: "translateX(-50%)", zIndex: 11, background: "#121214", color: "#a1a1aa", border: "1px solid #1c1c1f", borderRadius: 10, padding: "6px 12px", fontSize: 12 }}>{ran} <button onClick={() => setRan(null)} aria-label="dismiss" style={{ background: "none", border: 0, color: "#71717a", cursor: "pointer" }}>×</button></div>}
        {note && (
          <div role="status" style={{ position: "absolute", left: "50%", bottom: 18, transform: "translateX(-50%)", zIndex: 11, background: "#121214", color: "#e4e4e7", border: "1px solid #1c1c1f", borderRadius: 10, padding: "8px 14px", fontSize: 13, maxWidth: 560 }}>
            {note} <button onClick={() => setNote(null)} aria-label="dismiss" style={{ background: "none", border: 0, color: "#71717a", cursor: "pointer" }}>×</button>
          </div>
        )}
        {panelOpen && (
          <div style={{ position: "absolute", top: 12, right: 12, bottom: 12, zIndex: 10, display: "flex" }}>
            <Panel
              onPlace={(elements) => setPlaced((all) => [...all, ...elements])}
              onClose={() => setPanelOpen(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
