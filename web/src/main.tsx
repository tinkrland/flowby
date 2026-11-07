/**
 * main.tsx: the dev harness, and the only file that knows the app exists.
 *
 * it fetches the graph `bin/flowby --json graph` wrote and draws it. everything the canvas shows is
 * therefore python's output, not a fixture: if the graph command breaks, this page shows nothing
 * and says so.
 *
 * state: designed. it bundles; nobody has panned it.
 */

import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import { NodeCanvas } from "./NodeCanvas";
import { Panel, type PlacedElement } from "./Panel";

type GraphDocument = {
  title: string;
  pipeline: { nodes: any[]; wires: any[] };
};

function App() {
  const [doc, setDoc] = useState<GraphDocument | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [placed, setPlaced] = useState<PlacedElement[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/graph.json")
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json() as Promise<GraphDocument>;
      })
      .then(setDoc)
      .catch((problem: Error) => setError(`run npm run graph. ${problem.message}`));
  }, []);

  if (error) return <p style={{ padding: 16, color: "#f87171" }}>{error}</p>;
  if (!doc) return <p style={{ padding: 16, color: "#71717a" }}>reading the graph…</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          display: "flex",
          gap: 12,
          alignItems: "baseline",
          padding: "10px 16px",
          borderBottom: "1px solid #1c1c1f",
        }}
      >
        <strong>{doc.title}</strong>
        <span style={{ color: "#71717a", fontSize: 12 }}>
          {doc.pipeline.nodes.length} nodes, {doc.pipeline.wires.length} wires
          {placed.length > 0 && `, ${placed.length} placed from the panel`}
        </span>
        <button
          onClick={() => setPanelOpen((open) => !open)}
          style={{ marginLeft: "auto", background: "#27272a", color: "#e4e4e7", border: 0, borderRadius: 8, padding: "6px 12px", cursor: "pointer" }}
        >
          new node
        </button>
      </header>
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <NodeCanvas pipeline={doc.pipeline} />
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
