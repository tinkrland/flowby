/** the entry the kits render test bundles: one kit's rows, drawn by the real component. */
import { KitRowView } from "../src/KitRow";
import { kitView, kitsButton } from "../src/kitsmenu.mjs";

export function RenderKit({ kit, placing = null }: { kit: any; placing?: string | null }) {
  const v = kitView(kit);
  return (
    <ul>
      {v.rows.map((r: any) => <KitRowView key={r.id} r={r} placing={placing} onPlace={() => {}} />)}
    </ul>
  );
}

export function KitButton({ kits, reachable = true }: { kits: any[]; reachable?: boolean }) {
  return <span data-title={kitsButton(kits, { reachable }).title} />;
}
