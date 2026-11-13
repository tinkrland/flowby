/**
 * Icons: the rail's glyphs, in one registry, drawn to a single grid.
 *
 * the owner wants these to come from **Streamline** (owner, 2026-11-13). Streamline ships exported
 * SVG, not a runtime package, so the swap is deliberately one line per glyph: replace the `d` string
 * with the exported path and keep the grid. every icon here is 24x24, `currentColor`, 1.5px stroke,
 * round joins, no fill — which is Streamline's outline preset, so an export drops in without a
 * restyle. nothing in the rail reaches for an icon outside this file.
 *
 * these are drawn here rather than copied: Streamline's library is licensed per seat, and an icon
 * file committed to a public repo would be a licence problem, not just a design choice.
 */

type Glyph = { d: string; extra?: string };

export const ICONS: Record<string, Glyph> = {
  plus: { d: "M12 5.5v13M5.5 12h13" },
  library: { d: "M3.5 7.5a2 2 0 0 1 2-2h3.2l1.8 2h7a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-12a2 2 0 0 1-2-2z" },
  command: { d: "M4.5 5.5h15v13h-15zM8 10l2.5 2.5L8 15M13.5 15h3" },
  nodes: { d: "M4.5 4.5h5.5v5.5h-5.5zM4.5 14h5.5v5.5h-5.5zM14 4.5h5.5v5.5H14M16.75 14v5.5M14 16.75h5.5" },
  settings: { d: "M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2M6 6l1.6 1.6M16.4 16.4 18 18M18 6l-1.6 1.6M7.6 16.4 6 18" },
  run: { d: "M8.5 5.5 19 12 8.5 18.5z" },
};

/** one glyph, at whatever size the rail asks for. */
export function Icon({ name, size = 18, stroke = 1.5 }: { name: string; size?: number; stroke?: number }) {
  const glyph = ICONS[name] ?? ICONS.nodes;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable="false">
      <path d={glyph.d} />
    </svg>
  );
}
