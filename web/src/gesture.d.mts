export function carriesFiles(types: ArrayLike<string> | undefined): boolean;
export function dragState(args: { types?: ArrayLike<string>; over?: string | null; nodes?: Record<string, { label: string; accepts: boolean }> }):
  { active: boolean; target: string | null; verb: string | null; refuses?: string | null };
export function dropTarget(args: { over?: string | null; nodes?: Record<string, { label: string; accepts: boolean }>; count?: number }):
  { action: "create" | "replace" | "replace-first" | "refuse"; count?: number; node?: string; extra?: number; note?: string; reason?: string };
export function typing(target: { tagName?: string; type?: string; isContentEditable?: boolean } | null): boolean;
export function readPaste(args: { files?: File[]; hasText?: boolean; target?: { tagName?: string; type?: string; isContentEditable?: boolean } | null }):
  { take: File[]; why: string; silent: boolean };
export function nameForPaste(file: { name?: string; type?: string }, index: number, now?: Date): string;
export function layoutRow<T extends { width?: number; height?: number }>(items: T[], options?: { origin?: { x: number; y: number }; gap?: number; height?: number; max?: number }):
  (T & { box: { x: number; y: number; w: number; h: number } })[];
export function takeFiles(files: { name: string; bytes: Uint8Array }[]):
  { placed: { name: string; bytes: Uint8Array; plan: unknown; needs: "unpack" | null }[]; refused: { name: string; reason: string }[] };
