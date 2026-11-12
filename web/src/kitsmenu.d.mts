export interface KitMember { id: string; label: string; blurb: string; kind?: string; parent: string | null; preset?: string | null; state: string; runnable: boolean }
export interface KitData { id: string; label: string; blurb: string; members: KitMember[]; ready?: number; total?: number }
export interface KitRow { id: string; label: string; blurb: string; depth: number; state: string; word: string; usable: boolean }
export interface KitViewShape { id: string; label: string; blurb: string; ready: number; total: number; summary: string; rows: KitRow[] }
export const STATE_WORD: Readonly<Record<"listed" | "corpus" | "training" | "ready", string>>;
export function wordFor(state: unknown): string;
export function ordered(members: KitMember[] | null | undefined): (KitMember & { depth: number })[];
export function kitView(kit: KitData): KitViewShape;
export function kitsButton(kits: KitData[] | null | undefined, options?: { reachable?: boolean }): { label: string; tone: "up" | "idle" | "off"; title: string };
