import type { PlugView } from "./api.mjs";
export const STATES: readonly string[];
export const DOT: Readonly<Record<"up" | "down" | "unchecked", { hex: string; word: string }>>;
export function dotFor(state: unknown): { hex: string; word: string };
export function buttonState(plugs: PlugView[] | null | undefined, options?: { reachable?: boolean }): { label: string; tone: "up" | "down" | "idle" | "off"; title: string };
export interface FormShape { label: string; provider: string; endpoint: string; token: string; tunnel: boolean }
export const EMPTY_FORM: Readonly<FormShape>;
export function isLoopback(endpoint: string): boolean;
export type Providers = Record<string, { kind?: "server" | "hosted"; label?: string; note?: string }>;
export function kindOf(provider: string, providers?: Providers): "server" | "hosted";
export function formWords(provider: string, providers?: Providers): { endpoint: string; tokenLabel: string; tokenHint: string; tunnel: boolean; submit: string; after: string };
export function hints(form: FormShape, providers?: Providers): { field: "label" | "endpoint" | "token"; say: string }[];
export function canSubmit(form: FormShape, providers?: Providers): boolean;
export function body(form: FormShape, providers?: Providers): { label: string; provider: string; endpoint: string; tunnel: boolean; token?: string };
export function clear(): FormShape;
export function rowOf(plug: PlugView): { id: string; title: string; sub: string; dot: { hex: string; word: string }; detail: string; models: string[]; version: string | null; latency: string | null; hasToken: boolean; checked: Date | null; action: "check" | "check again" | null; hosted: boolean };
export function ago(checkedAt: Date | null, now?: number): string;
export const STALE_AFTER_S: number;
export function isStale(plug: PlugView, now?: number): boolean;
