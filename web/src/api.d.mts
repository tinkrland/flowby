export class Unreachable extends Error { constructor(base: string) }
export class Refused extends Error { status: number; constructor(message: string, status: number) }
export function baseUrl(env?: Record<string, string | undefined>): string;
export interface PlugView { id: string; label: string; provider: string; provider_label: string; kind?: "server" | "hosted"; endpoint: string; state: string; detail: string; models: string[]; version: string | null; checked_at: number | null; latency_ms: number | null; tunnel: boolean; has_token: boolean }
export interface PlugList { plugs: PlugView[]; providers: Record<string, { kind?: "server" | "hosted"; label: string; note: string }>; auth: string }
export interface Client {
  get(path: string): Promise<any>;
  post(path: string, payload?: unknown): Promise<any>;
  plugs(): Promise<PlugList>;
  addPlug(form: { label: string; provider: string; endpoint: string; token?: string; tunnel?: boolean }): Promise<{ plug: PlugView; plugs: PlugView[] }>;
  checkPlug(id: string): Promise<{ plug: PlugView; plugs: PlugView[] }>;
  removePlug(id: string): Promise<{ plugs: PlugView[] }>;
  kits(): Promise<any>;
  looks(): Promise<any>;
  placeLook(look: string, extra?: { preset?: string; mode?: string }): Promise<any>;
}
export function client(options?: { base?: string; fetcher?: typeof fetch }): Client;
