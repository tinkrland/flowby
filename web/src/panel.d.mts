/** types for panel.mjs, so the React skin is checked against a contract and not against inference. */

export interface QueueItem {
  id: string;
  name: string;
  bytes: Uint8Array;
  type: string;
  kind: string | null;
  via: string;
  warning: string | null;
  note: string | null;
  status: string;
}

export type ViewQueueItem = Omit<QueueItem, "bytes"> & { size: number };

export interface Refused { name: string; reason: string }

export interface FigmaFrame {
  id: string;
  name: string;
  type: string;
  width: number | null;
  height: number | null;
  section: string | null;
}

export interface Cost {
  requests: number;
  naive: number;
  minutes: number;
  fits: boolean;
  note: string;
  seat: string;
  limit: { per: "month" | "minute"; amount: number };
}

export interface ParsedLink { fileKey: string; branch: string | null; nodeId: string | null; type: string; name: string | null }

export interface FigmaState {
  link: string;
  token: string;
  seat: string;
  frames: FigmaFrame[];
  missing: string[];
  picked: string[];
  step: "link" | "token" | "pick";
  error: string | null;
  cost: Cost | null;
  parsed?: ParsedLink;
}

export interface PanelElement {
  kind: string;
  label: string;
  asset: string;
  bytes: number;
  source: Record<string, unknown>;
  warning?: string | null;
  sniffed?: string;
  via?: string;
}

export interface PanelState {
  open: boolean;
  door: "upload" | "figma";
  queue: QueueItem[];
  placed: PanelElement[];
  refused: Refused[];
  figma: FigmaState;
  seq: number;
}

export type Action =
  | { type: "open"; door?: "upload" | "figma" }
  | { type: "close" }
  | { type: "door"; door: "upload" | "figma" }
  | { type: "files"; files: { name: string; bytes: Uint8Array }[] }
  | { type: "unpacked"; id: string; files: { name: string; bytes: Uint8Array }[] }
  | { type: "unqueue"; id: string }
  | { type: "dismiss"; index: number }
  | { type: "placed"; ids: string[]; elements: PanelElement[]; failed?: { name?: string; id?: string; reason: string }[] }
  | { type: "figma-link"; link: string }
  | { type: "figma-token"; token: string }
  | { type: "figma-seat"; seat: string }
  | { type: "figma-parsed"; parsed: ParsedLink }
  | { type: "figma-frames"; frames: FigmaFrame[]; missing?: string[] }
  | { type: "figma-pick"; id: string }
  | { type: "figma-pick-all"; ids?: string[] }
  | { type: "figma-error"; error: string }
  | { type: "figma-reset" };

export interface PanelView {
  open: boolean;
  door: "upload" | "figma";
  queue: ViewQueueItem[];
  placed: number;
  refused: Refused[];
  figma: Omit<FigmaState, "token"> & { hasToken: boolean; token: string | null };
  canPlace: boolean;
  canImport: boolean;
}

export const FIGMA_API: string;
export function initial(): PanelState;
export function reduce(state: PanelState, action: Action): PanelState;
export function view(state: PanelState): PanelView;
export function mask(token: string): string | null;

export interface FigmaClient {
  nodes(fileKey: string, ids: string[]): Promise<any>;
  file(fileKey: string): Promise<any>;
  images(fileKey: string, ids: string[], scale?: number): Promise<any>;
}
export function figmaClient(options: { token: string; fetchFn?: typeof fetch }): FigmaClient;
export function framesFromResponse(response: any, wanted?: string[] | null): { frames: FigmaFrame[]; missing: string[] };
export function importPicked(options: {
  client: FigmaClient;
  parsed: ParsedLink;
  frames: FigmaFrame[];
  picked: string[];
  download: (url: string) => Promise<Uint8Array>;
  seat: string;
  subtle?: SubtleCrypto;
}): Promise<{ elements: PanelElement[]; failed: { id: string; reason: string }[]; requests: number; cost: Cost }>;
