import type { Cost, FigmaFrame, ParsedLink } from "./panel.mjs";

export class IntakeRefused extends Error {}
export const ELEMENT_KINDS: Readonly<Record<string, string>>;
export const MAX_BYTES: number;
export const IMAGE_BATCH: number;
export const ZIP_LIMITS: Readonly<{ entries: number; total: number; ratio: number }>;
export function sniff(bytes: Uint8Array | ArrayBuffer): string | null;
export function classify(file: { name?: string; bytes: Uint8Array; size?: number }): {
  type: string; kind: string | null; via: string; note: string | null; warning: string | null;
};
export function digest(bytes: Uint8Array, subtle?: SubtleCrypto): Promise<string>;
export function toElement(file: { name: string; bytes: Uint8Array }, options?: { subtle?: SubtleCrypto }): Promise<import("./panel.mjs").PanelElement>;
export function unpackZip(
  bytes: Uint8Array,
  unzip: (data: Uint8Array, options?: any) => Record<string, Uint8Array>,
  limits?: { entries: number; total: number; ratio: number },
): { files: { name: string; bytes: Uint8Array }[]; skipped: { name: string; reason: string }[] };
export function parseFigma(link: string): ParsedLink;
export function importCost(frames: number, options?: { seat?: string; batch?: number }): Cost;
export function planImport(frames: number, options?: { seat?: string; batch?: number }): Cost;
export function framesOf(response: any, wanted?: string[] | null): { frames: FigmaFrame[]; missing: string[] };
export function exportScale(frame: { width: number | null; height: number | null }, options?: { want?: number; cap?: number }): { scale: number; reduced: boolean; known: boolean; pixels?: number };
export function imageUrls(response: any, ids: string[]): { ok: { id: string; url: string }[]; failed: { id: string; reason: string }[] };
