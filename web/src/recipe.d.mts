export interface CardInput { label: string; means?: string; required?: boolean; example?: { kind: string; value: unknown } | null; target?: { preset: string; param: string } }
export interface CardSlot { preset: string; slot: string; filled?: boolean; required?: boolean }
export interface CardRow { preset: string; name: string; value: unknown; means?: string }
export interface CardShape {
  /** set by the server: which element on the board this card came from */
  element?: string;
  name: string; brief?: string; version?: string; author?: string; output?: string; category?: string;
  inputs?: CardInput[]; slots?: CardSlot[]; advanced?: CardRow[]; hidden?: CardRow[];
  needs?: { runtime?: string; gpu?: boolean; cost?: string; weights?: string[]; files?: string[]; paid?: boolean };
  run?: { label?: string; enabled?: boolean; blocked_by?: string[] };
}
export interface ViewInput { label: string; mark: string; required: boolean; example: string; means: string; where: string }
export interface ViewSlot { label: string; mark: string; required: boolean; filled: boolean; means: string }
export interface ViewRow { label: string; value: string; means: string }
export interface ViewFixed { label: string; where: string; value: string; means: string }
export interface CardViewShape {
  name: string; stamp: string; brief: string; output: string; category: string;
  inputs: ViewInput[]; slots: ViewSlot[]; advanced: ViewRow[]; fixed: ViewFixed[];
  needs: { key: string; says: string }[]; run: { label: string; enabled: boolean; why: string }; wanted: number;
}
export interface ShelfRow { element: string; name: string; version: string; brief: string; output: string; ready: boolean }
export interface ShelfViewShape { rows: ShelfRow[]; empty: string; reachable: boolean }
export function cardView(card: CardShape | null | undefined): CardViewShape | null;
export function shelfView(recipes: CardShape[] | null | undefined, options?: { reachable?: boolean }): ShelfViewShape;
