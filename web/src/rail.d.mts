/** types for rail.mjs: the shapes the rail and its popover hand to react. */

export type RailSlot = { id: string; icon: string; label: string; hint: string; key?: string; on: boolean; why: string | null };
export type NodeRow = { name: string; label: string; blurb: string; from: string | null; to: string | null; stage: string; estimate: number | null };
export type NodeGroup = { dtype: string; hex: string; means: string; rows: NodeRow[]; count: number };

export declare const RAIL: readonly Omit<RailSlot, "on" | "why">[];
export declare const RUN: { id: string; icon: string; label: string; hint: string };
export declare const PENDING: Readonly<Record<string, string>>;
export declare function railState(state?: { hasSelection?: boolean; narrow?: boolean }): { items: RailSlot[]; run: RailSlot; visible: boolean };
export declare function nodeGroups(presets: any[]): { groups: NodeGroup[]; total: number; empty: string };
export declare function estimateText(minutes: number | null | undefined): string;
