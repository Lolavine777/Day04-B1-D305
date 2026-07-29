import type { AgentEvent, ProviderName } from "@/lib/types";

interface StreamChatInput {
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  provider: ProviderName;
  model?: string;
  version: string;
}

interface StreamChatOptions {
  signal: AbortSignal;
  onEvent: (event: AgentEvent) => void;
}

function parseEventBlock(block: string): AgentEvent | null {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");

  if (!data) {
    return null;
  }

  try {
    return JSON.parse(data) as AgentEvent;
  } catch {
    return {
      type: "run_failed",
      message: "The server returned an unreadable stream event.",
    };
  }
}

export async function streamChat(
  input: StreamChatInput,
  options: StreamChatOptions,
): Promise<void> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(input),
    signal: options.signal,
  });

  if (!response.ok) {
    let detail = "";
    try {
      const payload = (await response.json()) as { detail?: unknown };
      detail =
        typeof payload.detail === "string"
          ? payload.detail
          : JSON.stringify(payload.detail ?? "");
    } catch {
      detail = await response.text();
    }
    throw new Error(
      detail || `The API returned HTTP ${response.status}.`,
    );
  }

  if (!response.body) {
    throw new Error("This browser cannot read the response stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const event = parseEventBlock(block);
      if (event) {
        options.onEvent(event);
      }
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    const event = parseEventBlock(buffer);
    if (event) {
      options.onEvent(event);
    }
  }
}
