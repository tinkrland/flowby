/**
 * the entry the render test bundles. it exists so the test renders the real component rather than a
 * copy of its markup: `tests/render.test.mjs` bundles this with esbuild and calls it with a payload.
 */
import { Inspector } from "../src/Inspector";
import { panel, summary } from "../src/inspector.mjs";

export function RenderPanel({ id, doc, onClose }: { id: string; doc: any; onClose: () => void }) {
  const model = panel(id, doc);
  if (!model) return <em>no panel</em>;
  return <Inspector model={model} board={summary(doc)} onClose={onClose} />;
}
