/** types for rail.mjs: the shapes the rail and its popover hand to react. */

export type RailSlot = { id: string; icon: string; label: string; hint: string; key?: string; on: boolean; why: string | null };
export type NodeRow = { name: string; label: string; blurb: string; from: string | null; to: string | null; stage: string; estimate: number | null; variants?: number;
  /** what one variant is called, declared by the preset when the wire noun would be wrong */
  variantNoun?: string | null;
  /** the counted name a person reads: "6 materials" when the card makes six */
  show?: string };
export type NodeGroup = { dtype: string; hex: string; means: string; rows: NodeRow[]; count: number };

export declare const RAIL: readonly Omit<RailSlot, "on" | "why">[];
export declare const RUN: { id: string; icon: string; label: string; hint: string };
export declare const PENDING: Readonly<Record<string, string>>;
export declare function railState(state?: { hasSelection?: boolean; narrow?: boolean }): { items: RailSlot[]; run: RailSlot; visible: boolean };
export declare function nodeGroups(presets: any[]): { groups: NodeGroup[]; total: number; empty: string };
export declare function countedName(row: { label?: string; variants?: number;
  /** what one variant is called, declared by the preset when the wire noun would be wrong */
  variantNoun?: string | null; to?: string | null }): string;
export declare function estimateText(minutes: number | null | undefined): string;
