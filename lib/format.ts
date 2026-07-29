import type { RunMetrics } from "@/lib/types";

function numeric(
  usage: Record<string, unknown> | undefined,
  keys: string[],
): number | null {
  for (const key of keys) {
    const value = usage?.[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }
  return null;
}

export function metricsFromEvent(
  usage: Record<string, unknown> | undefined,
  latencyMs?: number,
  ttftMs?: number | null,
): RunMetrics {
  const inputTokens = numeric(usage, ["prompt_tokens", "input_tokens"]);
  const outputTokens = numeric(usage, ["completion_tokens", "output_tokens"]);
  const reportedTotal = numeric(usage, ["total_tokens"]);
  const totalTokens =
    reportedTotal ??
    (inputTokens !== null && outputTokens !== null
      ? inputTokens + outputTokens
      : null);

  return {
    latencyMs:
      typeof latencyMs === "number" && Number.isFinite(latencyMs)
        ? latencyMs
        : null,
    ttftMs:
      typeof ttftMs === "number" && Number.isFinite(ttftMs) ? ttftMs : null,
    inputTokens,
    outputTokens,
    totalTokens,
    cost: numeric(usage, ["cost", "total_cost", "estimated_cost"]),
  };
}

export function formatDuration(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`;
  }
  return `${(value / 1000).toFixed(value < 10_000 ? 2 : 1)} s`;
}

export function formatTokens(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return new Intl.NumberFormat("en-US", {
    notation: value >= 10_000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatCost(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  if (value === 0) {
    return "$0.0000";
  }
  if (value < 0.01) {
    return `$${value.toFixed(5)}`;
  }
  return `$${value.toFixed(3)}`;
}

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function compactModelName(value: string | null | undefined): string {
  if (!value) {
    return "Provider default";
  }
  const parts = value.split("/");
  return parts[parts.length - 1] || value;
}
