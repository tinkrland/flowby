export type Shape = "circle" | "oval";
export interface PortLike { dtype: string; role?: string | null; many?: boolean }
export interface NodeLike {
  id?: string; op?: string; label?: string;
  inputs?: Record<string, PortLike>; outputs?: Record<string, PortLike>; params?: Record<string, unknown>;
}
export interface CardRow { side: string; name: string; dtype?: string; role?: string | null; shape?: Shape; hex?: string; value?: string; raw?: unknown; connected?: boolean }
export interface CardModel {
  id?: string; title?: string; kind?: string;
  inputs: CardRow[]; properties: CardRow[]; outputs: CardRow[];
  hidden: number; foldLabel: string | null; isElement: boolean;
}
export const SOCKET: Readonly<Record<Shape, { w: number; h: number }>>;
export const CARD: Readonly<{ head: number; row: number; fold: number; pad: number; preview: number; width: number }>;
export const VISIBLE_PARAMS: number;
export function socketShape(port: PortLike): Shape;
export function formatValue(value: unknown): string;
export function isTunable(name: string, value: unknown): boolean;
export function cardOf(node: NodeLike, options?: { expanded?: boolean; visible?: number; connected?: Set<string> }): CardModel;
export function connectedPorts(pipeline: { wires?: { from: { node: string; port: string }; to: { node: string; port: string } }[] }): Map<string, Set<string>>;
export const IDLE_OPACITY: number;
export function socketOpacity(row: { connected?: boolean }): number;
export function cardHeight(card: CardModel, options?: { preview?: boolean }): number;
export function runnable(node: NodeLike): boolean;
export function executeState(selectedIds: string[], nodesById: Record<string, NodeLike & { label: string }>): { visible: boolean; label: string | null; count: number };
export function actionsFor(node: NodeLike): { id: string; label: string; primary?: boolean }[];

export interface Preset { name: string; label: string; blurb: string; stage: string; state?: string; from: string; to: string; models?: string[]; estimate?: number | null; applies_to?: string[] }
export interface Chip { dtype: string; label: string; hex: string }
export interface CommandRow {
  id: string; label: string; blurb: string; stage: string; state?: string;
  signature: { from: string; to: string; chips: Chip[] };
  models: string[]; estimate: number | null; appliesTo: string[]; search: string;
}
export function commandRows(presets: Preset[]): CommandRow[];
export function searchCommands(rows: CommandRow[], query?: string, options?: { appliesTo?: string | null }): CommandRow[];
export function quickConnect(rows: CommandRow[], target: { side: "in" | "out"; dtype: string; role?: string | null }): { side: string; dtype: string; role: string | null; options: CommandRow[]; empty: string | null };
export function frameNode(box: { x: number; y: number; width: number; height: number }, pane: { width: number; height: number }, options?: { fill?: number; minZoom?: number; maxZoom?: number }): { x: number; y: number; zoom: number };
