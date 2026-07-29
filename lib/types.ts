export type ProviderName = "openrouter" | "openai" | "anthropic" | "gemini";

export type MessageStatus =
  | "complete"
  | "streaming"
  | "waiting"
  | "error"
  | "cancelled";

export type ToolStatus = "running" | "success" | "error";

export interface UsageMetrics {
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  cost: number | null;
}

export interface RunMetrics extends UsageMetrics {
  latencyMs: number | null;
  ttftMs: number | null;
}

export interface ToolTrace {
  id: string;
  name: string;
  args: unknown;
  result?: unknown;
  status: ToolStatus;
  latencyMs?: number | null;
  round: number;
}

export interface Clarification {
  question: string;
  responseType: "text" | "yes_no" | "choice";
  options: string[];
}

export interface RunMetadata {
  runId?: string;
  provider?: ProviderName;
  model?: string | null;
  streamMode?: string;
  artifactVersion?: string;
  status?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  status: MessageStatus;
  tools?: ToolTrace[];
  metrics?: RunMetrics;
  clarification?: Clarification;
  run?: RunMetadata;
  errorDetail?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface RuntimeConfig {
  provider: ProviderName;
  provider_ready: boolean;
  model: string | null;
  tool_count: number;
  blocked_tools: string[];
  artifact: {
    version?: string;
    artifact_version?: string;
    [key: string]: unknown;
  };
}

export interface AgentEvent {
  type: string;
  run_id?: string;
  round?: number;
  delta?: string;
  tool_id?: string;
  tool?: string;
  args?: unknown;
  result?: unknown;
  status?: string;
  message?: string;
  detail?: string;
  assistant_text?: string;
  latency_ms?: number;
  ttft_ms?: number | null;
  usage?: Record<string, unknown>;
  provider?: ProviderName;
  model?: string | null;
  stream_mode?: string;
  artifact?: {
    version?: string;
    artifact_version?: string;
    [key: string]: unknown;
  };
  has_tool_calls?: boolean;
  [key: string]: unknown;
}
