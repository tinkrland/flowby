/**
 * RecipeCard: the card a recipe gets, drawn in the rail's library panel.
 *
 * two exports on purpose. `RecipeCardBody` is pure: it takes the view model from recipe.mjs and draws it,
 * which is what the render test mounts with no server and no fetch. `RecipeShelf` is the one that talks
 * to python. keeping the fetch out of the drawing is why the test can assert what the card claims.
 *
 * the card is drawn in this order because it is the order a person needs it: what it is, what it wants
 * from you, what it will not let you change, what it needs to run, then the button.
 */

import { useCallback, useMemo, useState } from "react";

import { baseUrl, client } from "./api.mjs";
import { cardView, shelfView } from "./recipe.mjs";
import type { CardShape, CardViewShape } from "./recipe.mjs";

const N = { bg: "#121214", line: "#26262a", text: "#e4e4e7", mute: "#71717a", dim: "#a1a1aa", accent: "#a78bfa" };

const Row = ({ children }: { children: React.ReactNode }) => (
  <div style={{ display: "flex", gap: 8, alignItems: "baseline", lineHeight: 1.45 }}>{children}</div>
);

const Mark = ({ mark }: { mark: string }) => (
  // a required mark is a fact, so it is drawn in the text colour rather than as decoration
  <span aria-hidden style={{ width: 8, color: mark ? N.text : N.line, fontVariant: "tabular-nums" }}>{mark || "·"}</span>
);

/** the card itself. everything it says comes from the view model, so the panel cannot invent a claim. */
export function RecipeCardBody({ view, onRun }: { view: CardViewShape; onRun?: () => void }) {
  // the advanced fold is closed by default: one seed does not earn the space above the button
  const [open, setOpen] = useState(false);
  return (
    <article aria-label={`recipe ${view.name}`} style={{ color: N.text, fontSize: 12.5 }}>
      <header style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <h4 style={{ margin: 0, fontSize: 13.5, fontWeight: 600 }}>{view.name}</h4>
        <span style={{ marginLeft: "auto", color: N.mute, fontVariant: "tabular-nums" }} title="the version this card describes">
          {view.stamp}
        </span>
      </header>
      <p style={{ margin: "3px 0 0", color: N.dim, lineHeight: 1.45 }}>{view.brief}</p>

      {view.inputs.length > 0 && (
        <section style={{ marginTop: 10 }}>
          <div style={{ color: N.mute, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>inputs</div>
          <ul style={{ listStyle: "none", margin: "5px 0 0", padding: 0, display: "grid", gap: 5 }}>
            {view.inputs.map((input) => (
              <li key={input.label}>
                <Row>
                  <Mark mark={input.mark} />
                  <span>{input.label}</span>
                  <span style={{ marginLeft: "auto", color: N.mute, fontVariant: "tabular-nums" }} title={input.where}>
                    {input.example}
                  </span>
                </Row>
                {input.means && <div style={{ marginLeft: 16, color: N.mute, fontSize: 11.5 }}>{input.means}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.slots.length > 0 && (
        <section style={{ marginTop: 10 }}>
          <div style={{ color: N.mute, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>slots</div>
          <ul style={{ listStyle: "none", margin: "5px 0 0", padding: 0, display: "grid", gap: 4 }}>
            {view.slots.map((slot) => (
              <li key={slot.label}>
                <Row>
                  <Mark mark={slot.mark} />
                  <span style={{ color: slot.filled ? N.text : N.dim }}>{slot.label}</span>
                  <span style={{ marginLeft: "auto", color: slot.filled ? N.mute : "#fca5a5" }}>{slot.means}</span>
                </Row>
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.advanced.length > 0 && (
        <section style={{ marginTop: 10 }}>
          <button
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            style={{ display: "flex", gap: 6, alignItems: "center", background: "none", border: 0, padding: 0, color: N.mute, cursor: "pointer", fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}
          >
            <span aria-hidden>{open ? "▾" : "▸"}</span> advanced
          </button>
          {open && (
            <ul style={{ listStyle: "none", margin: "5px 0 0", padding: 0, display: "grid", gap: 4 }}>
              {view.advanced.map((row) => (
                <li key={row.label}>
                  <Row>
                    <span style={{ color: N.dim }}>{row.label}</span>
                    <span style={{ marginLeft: "auto", fontVariant: "tabular-nums" }}>{row.value}</span>
                  </Row>
                  <div style={{ color: N.mute, fontSize: 11.5 }}>{row.means}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {view.fixed.length > 0 && (
        <section style={{ marginTop: 10 }}>
          {/* not a fold: these are the settings nobody can change, and hiding that would be the lie */}
          <div style={{ color: N.mute, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>fixed by the chain</div>
          <ul style={{ listStyle: "none", margin: "5px 0 0", padding: 0, display: "grid", gap: 3 }}>
            {view.fixed.map((row) => (
              <li key={`${row.where}.${row.label}`} style={{ color: N.mute, fontSize: 11.5 }}>
                {row.where}.{row.label} runs at {row.value}
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.needs.length > 0 && (
        <section style={{ marginTop: 10, borderTop: `1px solid ${N.line}`, paddingTop: 8 }}>
          <div style={{ color: N.mute, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>what you need</div>
          <dl style={{ margin: "5px 0 0", display: "grid", gridTemplateColumns: "auto 1fr", gap: "3px 10px" }}>
            {view.needs.map((need) => (
              <div key={need.key} style={{ display: "contents" }}>
                <dt style={{ color: N.mute }}>{need.key}</dt>
                <dd style={{ margin: 0, color: N.dim }}>{need.says}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
        <button
          onClick={onRun}
          disabled={!view.run.enabled}
          title={view.run.why || `run ${view.name}`}
          style={{
            background: view.run.enabled ? "#27272a" : "#1b1b1f",
            color: view.run.enabled ? N.text : N.mute,
            border: `1px solid ${N.line}`, borderRadius: 8, padding: "6px 10px",
            cursor: view.run.enabled ? "pointer" : "default", fontSize: 12.5,
          }}
        >
          {view.run.label}
        </button>
        {/* the reason sits beside the button, not only in its tooltip: a tooltip is not a reason anyone reads */}
        {view.run.why && <div role="note" style={{ color: "#fca5a5", fontSize: 11.5 }}>{view.run.why}</div>}
      </div>
    </article>
  );
}

/** the shelf and the card together: the part that talks to python. */
export function RecipeShelf({ embedded = false }: { embedded?: boolean } = {}) {
  const api = useMemo(() => client({ base: baseUrl((import.meta as any).env ?? {}) }), []);
  const [cards, setCards] = useState<CardShape[] | null>(null);
  const [reachable, setReachable] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const answer = await api.recipes();
      setCards(answer.recipes ?? []);
      setReachable(true);
    } catch {
      setReachable(false);
      setCards([]);
    }
  }, [api]);

  // the panel loads when it is drawn: the library slot is where a person goes to look, so it fetches
  // then rather than when the board mounts
  useMemo(() => { void load(); }, [load]);

  const shelf = shelfView(cards, { reachable });
  const card = cards?.find((c) => c.element === picked) ?? cards?.[0];
  const view = cardView(card);

  if (!embedded) return null;   // the rail owns the open state; a second placement would be a popover

  return (
    <div style={{ color: N.text, fontSize: 12.5 }}>
      {shelf.empty && <div style={{ color: N.mute, lineHeight: 1.45 }}>{shelf.empty}</div>}
      {shelf.rows.length > 0 && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 4 }}>
          {shelf.rows.map((row) => {
            const active = (picked ?? cards?.[0]?.element) === row.element;
            return (
              <li key={row.element}>
                <button
                  onClick={() => setPicked(row.element)}
                  aria-pressed={active}
                  style={{ display: "flex", gap: 8, width: "100%", textAlign: "left", background: active ? "#27272a" : "none", border: `1px solid ${active ? N.line : "transparent"}`, borderRadius: 7, padding: "5px 8px", color: active ? N.text : N.dim, cursor: "pointer", fontSize: 12.5 }}
                >
                  <span>{row.name}</span>
                  <span style={{ marginLeft: "auto", color: N.mute, fontVariant: "tabular-nums" }}>{row.version}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {view && (
        <div style={{ marginTop: 10, borderTop: `1px solid ${N.line}`, paddingTop: 10 }}>
          <RecipeCardBody view={view} />
        </div>
      )}
    </div>
  );
}
