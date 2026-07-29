"use client";

import {
  Activity,
  ArrowClockwise,
  ArrowUp,
  CaretDown,
  Check,
  CheckCircle,
  ChatsCircle,
  Coins,
  Copy,
  DownloadSimple,
  Export,
  Gauge,
  List,
  Moon,
  Plus,
  SidebarSimple,
  Stop,
  Sun,
  Timer,
  Trash,
  WarningCircle,
  Wrench,
  X,
  XCircle,
} from "@phosphor-icons/react";
import { Theme, Tooltip } from "@radix-ui/themes";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import React, {
  FormEvent,
  KeyboardEvent,
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  compactModelName,
  formatCost,
  formatDuration,
  formatTime,
  formatTokens,
  metricsFromEvent,
} from "@/lib/format";
import { streamChat } from "@/lib/sse";
import {
  createSession,
  loadActiveSessionId,
  loadSessions,
  loadTheme,
  saveActiveSessionId,
  saveSessions,
  saveTheme,
} from "@/lib/storage";
import type {
  AgentEvent,
  ChatMessage,
  ChatSession,
  Clarification,
  ProviderName,
  RunMetrics,
  RuntimeConfig,
  ToolTrace,
} from "@/lib/types";

const SUGGESTIONS = [
  "Tóm tắt các tin AI nổi bật trong 7 ngày qua",
  "Tìm 5 bài viết gần đây của OpenAI trên X",
  "So sánh ba paper mới về agent memory",
  "Tra cứu chính sách trích nguồn nội bộ",
];

const EMPTY_METRICS: RunMetrics = {
  latencyMs: null,
  ttftMs: null,
  inputTokens: null,
  outputTokens: null,
  totalTokens: null,
  cost: null,
};

function createId(): string {
  return crypto.randomUUID();
}

function titleFromPrompt(value: string): string {
  const clean = value.replace(/\s+/g, " ").trim();
  return clean.length > 38 ? `${clean.slice(0, 38).trim()}...` : clean;
}

function jsonPreview(value: unknown): string {
  if (value === undefined) {
    return "Chưa có dữ liệu";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function clarificationFromResult(value: unknown): Clarification | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const result = value as Record<string, unknown>;
  if (result.awaiting_user !== true) {
    return undefined;
  }
  const responseType =
    result.response_type === "yes_no" || result.response_type === "choice"
      ? result.response_type
      : "text";
  return {
    question:
      typeof result.question === "string" ? result.question : "Bạn chọn phương án nào?",
    responseType,
    options: Array.isArray(result.options)
      ? result.options.filter((option): option is string => typeof option === "string")
      : [],
  };
}

function sessionDateLabel(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const sameDay =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();

  if (sameDay) {
    return formatTime(value);
  }
  return new Intl.DateTimeFormat("vi", {
    day: "2-digit",
    month: "2-digit",
  }).format(date);
}

function StatusMark({ status }: { status: ToolTrace["status"] }) {
  if (status === "running") {
    return <span className="toolStatusPulse" aria-label="Đang chạy" />;
  }
  if (status === "error") {
    return <XCircle aria-label="Lỗi" weight="fill" />;
  }
  return <CheckCircle aria-label="Hoàn tất" weight="fill" />;
}

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  provider: ProviderName;
  model: string;
  config: RuntimeConfig | null;
  apiStatus: "checking" | "ready" | "offline";
  onProviderChange: (provider: ProviderName) => void;
  onModelChange: (model: string) => void;
  onCreate: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onExport: () => void;
  onClose?: () => void;
}

const SessionSidebar = memo(function SessionSidebar({
  sessions,
  activeSessionId,
  provider,
  model,
  config,
  apiStatus,
  onProviderChange,
  onModelChange,
  onCreate,
  onSelect,
  onDelete,
  onExport,
  onClose,
}: SessionSidebarProps) {
  return (
    <aside className="sessionSidebar">
      <div className="brandRow">
        <div className="brandMark" aria-hidden="true">
          <span />
          <span />
        </div>
        <div className="brandType">
          <strong>Fieldwork</strong>
          <span>Research agent</span>
        </div>
        {onClose ? (
          <button className="iconButton sidebarClose" onClick={onClose} aria-label="Đóng lịch sử">
            <X />
          </button>
        ) : null}
      </div>

      <button className="newChatButton" onClick={onCreate}>
        <Plus weight="bold" />
        Nghiên cứu mới
      </button>

      <div className="sidebarSectionLabel">
        <span>Lịch sử</span>
        <span>{sessions.length}</span>
      </div>

      <nav className="sessionList" aria-label="Lịch sử hội thoại">
        {sessions.map((session) => (
          <div
            className={`sessionItem ${session.id === activeSessionId ? "active" : ""}`}
            key={session.id}
          >
            <button
              className="sessionSelect"
              onClick={() => onSelect(session.id)}
              aria-current={session.id === activeSessionId ? "page" : undefined}
            >
              <ChatsCircle />
              <span>
                <strong>{session.title}</strong>
                <small>{sessionDateLabel(session.updatedAt)}</small>
              </span>
            </button>
            <Tooltip content="Xóa hội thoại">
              <button
                className="sessionDelete"
                onClick={() => onDelete(session.id)}
                aria-label={`Xóa ${session.title}`}
              >
                <Trash />
              </button>
            </Tooltip>
          </div>
        ))}
      </nav>

      <div className="sidebarRuntime">
        <div className="sidebarSectionLabel">
          <span>Môi trường chạy</span>
          <span
            className={`apiState ${apiStatus}`}
            title={apiStatus === "ready" ? "API sẵn sàng" : "Trạng thái API"}
          >
            {apiStatus === "ready" ? "Online" : apiStatus === "offline" ? "Offline" : "Checking"}
          </span>
        </div>

        <label className="fieldLabel">
          <span>Nhà cung cấp</span>
          <select
            value={provider}
            onChange={(event) => onProviderChange(event.target.value as ProviderName)}
          >
            <option value="openrouter">OpenRouter</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="gemini">Gemini</option>
          </select>
        </label>

        <label className="fieldLabel">
          <span>Mô hình</span>
          <input
            value={model}
            onChange={(event) => onModelChange(event.target.value)}
            placeholder={config?.model ?? "Mặc định của provider"}
          />
        </label>

        <div className="runtimeMeta">
          <span>{config?.tool_count ?? 0} tools khả dụng</span>
          <span>{config?.artifact?.version ?? "v0"} prompt</span>
        </div>

        <div className="sidebarActions">
          <button onClick={onExport}>
            <DownloadSimple />
            Xuất JSON
          </button>
          <a href="http://127.0.0.1:8501" target="_blank" rel="noreferrer">
            <Export />
            Streamlit dự phòng
          </a>
        </div>
      </div>
    </aside>
  );
});

interface TracePanelProps {
  tools: ToolTrace[];
  metrics: RunMetrics;
  runStatus: string;
  model?: string | null;
  copiedId: string | null;
  onCopy: (id: string, value: unknown) => void;
  onClose?: () => void;
}

const TracePanel = memo(function TracePanel({
  tools,
  metrics,
  runStatus,
  model,
  copiedId,
  onCopy,
  onClose,
}: TracePanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <aside className="tracePanel">
      <div className="traceHeader">
        <div>
          <span className="panelEyebrow">Quan sát lượt chạy</span>
          <h2>Live trace</h2>
        </div>
        {onClose ? (
          <button className="iconButton" onClick={onClose} aria-label="Đóng live trace">
            <X />
          </button>
        ) : null}
      </div>

      <div className="runIdentity">
        <span className={`runIndicator ${runStatus}`} />
        <div>
          <strong>
            {runStatus === "streaming"
              ? "Đang xử lý"
              : runStatus === "error"
                ? "Lượt chạy lỗi"
                : "Lượt chạy gần nhất"}
          </strong>
          <span>{compactModelName(model)}</span>
        </div>
      </div>

      <div className="metricGrid">
        <Metric
          icon={<Timer />}
          label="TTFT"
          value={formatDuration(metrics.ttftMs)}
        />
        <Metric
          icon={<Gauge />}
          label="Latency"
          value={formatDuration(metrics.latencyMs)}
        />
        <Metric
          icon={<Activity />}
          label="Tokens"
          value={formatTokens(metrics.totalTokens)}
        />
        <Metric icon={<Coins />} label="Chi phí" value={formatCost(metrics.cost)} />
      </div>

      <div className="tokenBreakdown">
        <span>
          Input <strong>{formatTokens(metrics.inputTokens)}</strong>
        </span>
        <span>
          Output <strong>{formatTokens(metrics.outputTokens)}</strong>
        </span>
      </div>

      <div className="traceSectionTitle">
        <span>Tool activity</span>
        <span>{tools.length}</span>
      </div>

      <div className="toolList">
        {tools.length === 0 ? (
          <div className="traceEmpty">
            <Wrench />
            <strong>Chưa có tool call</strong>
            <span>Các bước tìm kiếm và xử lý dữ liệu sẽ xuất hiện tại đây.</span>
          </div>
        ) : (
          tools.map((tool) => {
            const isExpanded = Boolean(expanded[tool.id]);
            return (
              <div className={`toolItem ${tool.status}`} key={tool.id}>
                <button
                  className="toolSummary"
                  onClick={() =>
                    setExpanded((current) => ({
                      ...current,
                      [tool.id]: !current[tool.id],
                    }))
                  }
                  aria-expanded={isExpanded}
                >
                  <StatusMark status={tool.status} />
                  <span>
                    <strong>{tool.name}</strong>
                    <small>
                      Round {tool.round}
                      {typeof tool.latencyMs === "number"
                        ? ` · ${formatDuration(tool.latencyMs)}`
                        : ""}
                    </small>
                  </span>
                  <CaretDown className={isExpanded ? "rotated" : ""} />
                </button>

                {tool.status === "running" ? <div className="toolProgress" /> : null}

                <AnimatePresence initial={false}>
                  {isExpanded ? (
                    <motion.div
                      className="toolDetails"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.18 }}
                    >
                      <CodePanel
                        title="Tham số"
                        value={tool.args}
                        copied={copiedId === `${tool.id}-args`}
                        onCopy={() => onCopy(`${tool.id}-args`, tool.args)}
                      />
                      {tool.status !== "running" ? (
                        <CodePanel
                          title="Kết quả"
                          value={tool.result}
                          copied={copiedId === `${tool.id}-result`}
                          onCopy={() => onCopy(`${tool.id}-result`, tool.result)}
                        />
                      ) : null}
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
});

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="metric">
      <span className="metricLabel">
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function CodePanel({
  title,
  value,
  copied,
  onCopy,
}: {
  title: string;
  value: unknown;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <section className="codePanel">
      <header>
        <span>{title}</span>
        <button onClick={onCopy} aria-label={`Sao chép ${title.toLowerCase()}`}>
          {copied ? <Check /> : <Copy />}
          {copied ? "Đã chép" : "Sao chép"}
        </button>
      </header>
      <pre>{jsonPreview(value)}</pre>
    </section>
  );
}

interface MessageItemProps {
  message: ChatMessage;
  reduceMotion: boolean;
  onClarify: (value: string) => void;
  onRetry: (messageId: string) => void;
}

const MessageItem = memo(function MessageItem({
  message,
  reduceMotion,
  onClarify,
  onRetry,
}: MessageItemProps) {
  const assistant = message.role === "assistant";
  const isStreaming = message.status === "streaming";

  return (
    <motion.article
      className={`message ${message.role} ${message.status}`}
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.22 }}
    >
      {assistant ? (
        <div className="assistantRail">
          <span>F</span>
        </div>
      ) : null}

      <div className="messageBody">
        <div className="messageMeta">
          <strong>{assistant ? "Fieldwork" : "Bạn"}</strong>
          <time>{formatTime(message.createdAt)}</time>
          {isStreaming ? <span className="liveLabel">Live</span> : null}
        </div>

        {message.content ? (
          assistant ? (
            <div className="markdownBody">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ children, ...props }) => (
                    <a {...props} target="_blank" rel="noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {isStreaming ? <span className="streamCaret" aria-hidden="true" /> : null}
            </div>
          ) : (
            <p className="userText">{message.content}</p>
          )
        ) : isStreaming ? (
          <LiveActivity status={message.run?.status} />
        ) : null}

        {message.status === "waiting" && message.clarification ? (
          <ClarificationActions
            clarification={message.clarification}
            onSelect={onClarify}
          />
        ) : null}

        {message.status === "error" ? (
          <div className="messageError">
            <WarningCircle weight="fill" />
            <div>
              <strong>Không thể hoàn tất lượt chạy</strong>
              <span>{message.errorDetail || "Hãy kiểm tra API và thử lại."}</span>
            </div>
            <button onClick={() => onRetry(message.id)}>
              <ArrowClockwise />
              Thử lại
            </button>
          </div>
        ) : null}

        {message.status === "cancelled" ? (
          <div className="cancelledNote">Lượt chạy đã được dừng.</div>
        ) : null}

        {assistant && message.metrics && message.status === "complete" ? (
          <div className="messageMetrics">
            <span>{formatDuration(message.metrics.latencyMs)} latency</span>
            <span>{formatTokens(message.metrics.totalTokens)} tokens</span>
            <span>{formatCost(message.metrics.cost)}</span>
          </div>
        ) : null}
      </div>
    </motion.article>
  );
});

function LiveActivity({ status }: { status?: string }) {
  const label =
    status === "using_tools"
      ? "Đang dùng công cụ"
      : status === "thinking"
        ? "Đang tổng hợp"
        : "Đang kết nối mô hình";
  return (
    <div className="liveActivity" role="status">
      <span className="activityBars" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span>{label}</span>
    </div>
  );
}

function ClarificationActions({
  clarification,
  onSelect,
}: {
  clarification: Clarification;
  onSelect: (value: string) => void;
}) {
  const choices =
    clarification.responseType === "yes_no"
      ? ["Có", "Không"]
      : clarification.responseType === "choice"
        ? clarification.options
        : [];

  if (choices.length === 0) {
    return <div className="clarifyHint">Nhập câu trả lời ở ô chat bên dưới.</div>;
  }

  return (
    <div className="clarifyActions" aria-label="Các lựa chọn trả lời">
      {choices.map((choice) => (
        <button key={choice} onClick={() => onSelect(choice)}>
          {choice}
        </button>
      ))}
    </div>
  );
}

export function ChatWorkspace() {
  const reduceMotion = useReducedMotion();
  const [hydrated, setHydrated] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [provider, setProvider] = useState<ProviderName>("openrouter");
  const [model, setModel] = useState("");
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "ready" | "offline">(
    "checking",
  );
  const [draft, setDraft] = useState("");
  const [runningSessionId, setRunningSessionId] = useState<string | null>(null);
  const [leftDrawer, setLeftDrawer] = useState(false);
  const [rightDrawer, setRightDrawer] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const sessionsRef = useRef<ChatSession[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? sessions[0],
    [activeSessionId, sessions],
  );
  const messages = activeSession?.messages ?? [];
  const latestAssistant = [...messages]
    .reverse()
    .find((message) => message.role === "assistant");
  const latestMetrics = latestAssistant?.metrics ?? EMPTY_METRICS;
  const tools = messages.flatMap((message) => message.tools ?? []);
  const isRunning = runningSessionId !== null;

  useEffect(() => {
    const stored = loadSessions();
    const initialSessions = stored.length > 0 ? stored : [createSession()];
    const storedActive = loadActiveSessionId();
    const initialActive = initialSessions.some((session) => session.id === storedActive)
      ? storedActive!
      : initialSessions[0].id;

    setTheme(loadTheme());
    setSessions(initialSessions);
    sessionsRef.current = initialSessions;
    setActiveSessionId(initialActive);
    setHydrated(true);
  }, []);

  useEffect(() => {
    sessionsRef.current = sessions;
    if (!hydrated) {
      return;
    }
    const timer = window.setTimeout(() => saveSessions(sessions), 250);
    return () => window.clearTimeout(timer);
  }, [hydrated, sessions]);

  useEffect(() => {
    if (!hydrated || !activeSessionId) {
      return;
    }
    saveActiveSessionId(activeSessionId);
  }, [activeSessionId, hydrated]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    saveTheme(theme);
    document.documentElement.style.colorScheme = theme;
  }, [hydrated, theme]);

  useEffect(() => {
    let alive = true;
    setApiStatus("checking");
    fetch(`/api/config?provider=${provider}&version=v0`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Config unavailable");
        }
        return (await response.json()) as RuntimeConfig;
      })
      .then((value) => {
        if (!alive) {
          return;
        }
        setConfig(value);
        setApiStatus("ready");
      })
      .catch(() => {
        if (alive) {
          setConfig(null);
          setApiStatus("offline");
        }
      });
    return () => {
      alive = false;
    };
  }, [provider]);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) {
      return;
    }
    element.scrollTo({
      top: element.scrollHeight,
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }, [messages, reduceMotion]);

  useEffect(() => {
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setLeftDrawer(false);
        setRightDrawer(false);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  const mutateSession = useCallback(
    (sessionId: string, updater: (session: ChatSession) => ChatSession) => {
      setSessions((current) =>
        current.map((session) => (session.id === sessionId ? updater(session) : session)),
      );
    },
    [],
  );

  const patchMessage = useCallback(
    (
      sessionId: string,
      messageId: string,
      updater: (message: ChatMessage) => ChatMessage,
    ) => {
      mutateSession(sessionId, (session) => ({
        ...session,
        updatedAt: new Date().toISOString(),
        messages: session.messages.map((message) =>
          message.id === messageId ? updater(message) : message,
        ),
      }));
    },
    [mutateSession],
  );

  const executeRun = useCallback(
    async (
      sessionId: string,
      assistantId: string,
      history: ChatMessage[],
    ) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setRunningSessionId(sessionId);
      const roundBuffers = new Map<number, string>();
      let completed = false;
      let failed = false;

      const handleEvent = (event: AgentEvent) => {
        if (event.type === "connected") {
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            run: {
              ...message.run,
              runId: event.run_id,
              provider: event.provider,
              model: event.model,
              streamMode: event.stream_mode,
              artifactVersion:
                event.artifact?.artifact_version ?? event.artifact?.version,
              status: "connected",
            },
          }));
          return;
        }

        if (event.type === "round_started") {
          const round = event.round ?? 1;
          roundBuffers.set(round, "");
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            content: "",
            run: { ...message.run, status: "thinking" },
          }));
          return;
        }

        if (event.type === "assistant_delta" && event.delta) {
          const round = event.round ?? 1;
          const next = `${roundBuffers.get(round) ?? ""}${event.delta}`;
          roundBuffers.set(round, next);
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            content: next,
            run: { ...message.run, status: "streaming" },
          }));
          return;
        }

        if (event.type === "model_completed" && event.has_tool_calls) {
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            content: "",
            run: { ...message.run, status: "using_tools" },
          }));
          return;
        }

        if (event.type === "tool_started" && event.tool_id && event.tool) {
          const trace: ToolTrace = {
            id: event.tool_id,
            name: event.tool,
            args: event.args,
            status: "running",
            round: event.round ?? 1,
          };
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            content: "",
            tools: [...(message.tools ?? []).filter((tool) => tool.id !== trace.id), trace],
            run: { ...message.run, status: "using_tools" },
          }));
          return;
        }

        if (event.type === "tool_completed" && event.tool_id) {
          const clarification = clarificationFromResult(event.result);
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            tools: (message.tools ?? []).map((tool) =>
              tool.id === event.tool_id
                ? {
                    ...tool,
                    result: event.result,
                    args: event.args ?? tool.args,
                    latencyMs:
                      typeof event.latency_ms === "number" ? event.latency_ms : null,
                    status: event.status === "error" ? "error" : "success",
                  }
                : tool,
            ),
            clarification: clarification ?? message.clarification,
          }));
          return;
        }

        if (event.type === "run_completed") {
          completed = true;
          const waiting = event.status === "waiting_for_user";
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            content: event.assistant_text ?? message.content,
            status: waiting ? "waiting" : "complete",
            metrics: metricsFromEvent(
              event.usage,
              event.latency_ms,
              event.ttft_ms,
            ),
            run: { ...message.run, status: event.status ?? "complete" },
          }));
          return;
        }

        if (event.type === "run_failed") {
          failed = true;
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            status: "error",
            content: "",
            errorDetail: event.detail || event.message,
            run: { ...message.run, status: "error" },
          }));
        }
      };

      try {
        await streamChat(
          {
            messages: history
              .filter((message) => message.content.trim())
              .slice(-20)
              .map((message) => ({
                role: message.role,
                content: message.content,
              })),
            provider,
            model: model.trim() || undefined,
            version: "v0",
          },
          { signal: controller.signal, onEvent: handleEvent },
        );
        if (!completed && !failed && !controller.signal.aborted) {
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            status: "error",
            content: "",
            errorDetail: "Luồng dữ liệu kết thúc trước khi agent trả kết quả.",
            run: { ...message.run, status: "error" },
          }));
        }
      } catch (error) {
        if (controller.signal.aborted) {
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            status: "cancelled",
            content: message.content,
            run: { ...message.run, status: "cancelled" },
          }));
        } else {
          const detail = error instanceof Error ? error.message : "Unknown request error";
          patchMessage(sessionId, assistantId, (message) => ({
            ...message,
            status: "error",
            content: "",
            errorDetail: detail,
            run: { ...message.run, status: "error" },
          }));
          setApiStatus("offline");
        }
      } finally {
        abortRef.current = null;
        setRunningSessionId(null);
      }
    },
    [model, patchMessage, provider],
  );

  const sendPrompt = useCallback(
    (rawValue: string) => {
      const value = rawValue.trim();
      if (!value || isRunning || !activeSession) {
        return;
      }
      const now = new Date().toISOString();
      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: value,
        createdAt: now,
        status: "complete",
      };
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: "assistant",
        content: "",
        createdAt: now,
        status: "streaming",
        tools: [],
        metrics: EMPTY_METRICS,
        run: { provider, model: model || config?.model, status: "connecting" },
      };
      const history = [...activeSession.messages, userMessage];

      mutateSession(activeSession.id, (session) => ({
        ...session,
        title:
          session.messages.length === 0 ? titleFromPrompt(value) : session.title,
        updatedAt: now,
        messages: [...history, assistantMessage],
      }));
      setDraft("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      void executeRun(activeSession.id, assistantMessage.id, history);
    },
    [
      activeSession,
      config?.model,
      executeRun,
      isRunning,
      model,
      mutateSession,
      provider,
    ],
  );

  const retryMessage = useCallback(
    (messageId: string) => {
      if (!activeSession || isRunning) {
        return;
      }
      const assistantIndex = activeSession.messages.findIndex(
        (message) => message.id === messageId,
      );
      if (assistantIndex < 1) {
        return;
      }
      const baseHistory = activeSession.messages.slice(0, assistantIndex);
      const previous = baseHistory[baseHistory.length - 1];
      if (previous?.role !== "user") {
        return;
      }
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        status: "streaming",
        tools: [],
        metrics: EMPTY_METRICS,
        run: { provider, model: model || config?.model, status: "connecting" },
      };
      mutateSession(activeSession.id, (session) => ({
        ...session,
        updatedAt: new Date().toISOString(),
        messages: [...baseHistory, assistantMessage],
      }));
      void executeRun(activeSession.id, assistantMessage.id, baseHistory);
    },
    [
      activeSession,
      config?.model,
      executeRun,
      isRunning,
      model,
      mutateSession,
      provider,
    ],
  );

  const createNewSession = useCallback(() => {
    const session = createSession();
    setSessions((current) => [session, ...current]);
    setActiveSessionId(session.id);
    setLeftDrawer(false);
  }, []);

  const deleteSession = useCallback(
    (sessionId: string) => {
      const target = sessionsRef.current.find((session) => session.id === sessionId);
      if (!target || !window.confirm(`Xóa hội thoại "${target.title}"?`)) {
        return;
      }
      if (runningSessionId === sessionId) {
        abortRef.current?.abort();
      }
      setSessions((current) => {
        const remaining = current.filter((session) => session.id !== sessionId);
        if (remaining.length > 0) {
          if (sessionId === activeSessionId) {
            setActiveSessionId(remaining[0].id);
          }
          return remaining;
        }
        const replacement = createSession();
        setActiveSessionId(replacement.id);
        return [replacement];
      });
    },
    [activeSessionId, runningSessionId],
  );

  const exportSession = useCallback(() => {
    if (!activeSession) {
      return;
    }
    const blob = new Blob([JSON.stringify(activeSession, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${activeSession.title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "fieldwork-transcript"}.json`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }, [activeSession]);

  const copyValue = useCallback((id: string, value: unknown) => {
    void navigator.clipboard.writeText(jsonPreview(value));
    setCopiedId(id);
    window.setTimeout(() => setCopiedId(null), 1400);
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    sendPrompt(draft);
  };

  const handleComposerKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      sendPrompt(draft);
    }
  };

  const updateDraft = (value: string) => {
    setDraft(value);
    const element = textareaRef.current;
    if (element) {
      element.style.height = "auto";
      element.style.height = `${Math.min(element.scrollHeight, 180)}px`;
    }
  };

  const closeDrawers = () => {
    setLeftDrawer(false);
    setRightDrawer(false);
  };

  if (!hydrated) {
    return (
      <Theme appearance="dark" accentColor="blue" grayColor="slate" radius="medium">
        <div className="appBoot" aria-label="Đang tải ứng dụng">
          <div className="bootMark">
            <span />
            <span />
          </div>
          <div className="bootLine" />
        </div>
      </Theme>
    );
  }

  const currentStatus =
    latestAssistant?.status === "streaming"
      ? "streaming"
      : latestAssistant?.status === "error"
        ? "error"
        : "complete";

  return (
    <Theme
      appearance={theme}
      accentColor="blue"
      grayColor="slate"
      radius="medium"
      className={`appTheme ${theme}`}
    >
      <main className="workspace">
        <div className="desktopSidebar">
          <SessionSidebar
            sessions={sessions}
            activeSessionId={activeSession?.id ?? ""}
            provider={provider}
            model={model}
            config={config}
            apiStatus={apiStatus}
            onProviderChange={setProvider}
            onModelChange={setModel}
            onCreate={createNewSession}
            onSelect={(id) => setActiveSessionId(id)}
            onDelete={deleteSession}
            onExport={exportSession}
          />
        </div>

        <section className="chatPane">
          <header className="chatHeader">
            <div className="mobileHeaderActions">
              <Tooltip content="Mở lịch sử">
                <button
                  className="iconButton"
                  onClick={() => setLeftDrawer(true)}
                  aria-label="Mở lịch sử"
                >
                  <List />
                </button>
              </Tooltip>
            </div>

            <div className="chatTitle">
              <strong>{activeSession?.title ?? "New research"}</strong>
              <span>
                <i className={`connectionDot ${apiStatus}`} />
                {isRunning
                  ? "Đang stream"
                  : apiStatus === "ready"
                    ? "Sẵn sàng"
                    : apiStatus === "offline"
                      ? "API chưa kết nối"
                      : "Đang kiểm tra"}
              </span>
            </div>

            <div className="headerActions">
              <Tooltip content={theme === "dark" ? "Dùng giao diện sáng" : "Dùng giao diện tối"}>
                <button
                  className="iconButton"
                  onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
                  aria-label={theme === "dark" ? "Dùng giao diện sáng" : "Dùng giao diện tối"}
                >
                  {theme === "dark" ? <Sun /> : <Moon />}
                </button>
              </Tooltip>
              <Tooltip content="Mở live trace">
                <button
                  className="iconButton traceToggle"
                  onClick={() => setRightDrawer(true)}
                  aria-label="Mở live trace"
                >
                  <SidebarSimple />
                </button>
              </Tooltip>
            </div>
          </header>

          <div className="messageScroll" ref={scrollRef}>
            <div className="messageColumn">
              {messages.length === 0 ? (
                <section className="emptyState">
                  <div className="emptyGlyph" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span className="emptyKicker">Research workspace</span>
                  <h1>Bạn muốn tìm hiểu điều gì?</h1>
                  <p>
                    Đặt câu hỏi, theo dõi từng tool call và xem chi phí của lượt chạy
                    ngay khi agent làm việc.
                  </p>
                  <div className="suggestionGrid">
                    {SUGGESTIONS.map((suggestion, index) => (
                      <button key={suggestion} onClick={() => sendPrompt(suggestion)}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        {suggestion}
                        <ArrowUp />
                      </button>
                    ))}
                  </div>
                </section>
              ) : (
                messages.map((message) => (
                  <MessageItem
                    key={message.id}
                    message={message}
                    reduceMotion={Boolean(reduceMotion)}
                    onClarify={sendPrompt}
                    onRetry={retryMessage}
                  />
                ))
              )}
            </div>
          </div>

          <div className="composerZone">
            <form className="composer" onSubmit={submit}>
              <textarea
                ref={textareaRef}
                value={draft}
                rows={1}
                maxLength={50_000}
                onChange={(event) => updateDraft(event.target.value)}
                onKeyDown={handleComposerKey}
                placeholder="Nhập yêu cầu nghiên cứu..."
                aria-label="Yêu cầu nghiên cứu"
                disabled={isRunning}
              />
              <div className="composerFooter">
                <span>
                  {compactModelName(model || config?.model)}
                  <i />
                  Enter để gửi
                </span>
                {isRunning ? (
                  <button
                    className="stopButton"
                    type="button"
                    onClick={() => abortRef.current?.abort()}
                    aria-label="Dừng lượt chạy"
                  >
                    <Stop weight="fill" />
                  </button>
                ) : (
                  <button
                    className="sendButton"
                    type="submit"
                    disabled={!draft.trim() || apiStatus === "offline"}
                    aria-label="Gửi yêu cầu"
                  >
                    <ArrowUp weight="bold" />
                  </button>
                )}
              </div>
            </form>
            <p className="composerNote">
              Agent có thể mắc lỗi. Kiểm tra nguồn trước khi sử dụng kết quả.
            </p>
          </div>
        </section>

        <div className="desktopTrace">
          <TracePanel
            tools={tools}
            metrics={latestMetrics}
            runStatus={currentStatus}
            model={latestAssistant?.run?.model ?? config?.model}
            copiedId={copiedId}
            onCopy={copyValue}
          />
        </div>

        <AnimatePresence>
          {leftDrawer || rightDrawer ? (
            <motion.button
              className="drawerBackdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reduceMotion ? 0 : 0.18 }}
              onClick={closeDrawers}
              aria-label="Đóng bảng điều khiển"
            />
          ) : null}
        </AnimatePresence>

        <AnimatePresence>
          {leftDrawer ? (
            <motion.div
              className="drawer leftDrawer"
              initial={reduceMotion ? false : { x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: reduceMotion ? 0 : 0.24, ease: "easeOut" }}
            >
              <SessionSidebar
                sessions={sessions}
                activeSessionId={activeSession?.id ?? ""}
                provider={provider}
                model={model}
                config={config}
                apiStatus={apiStatus}
                onProviderChange={setProvider}
                onModelChange={setModel}
                onCreate={createNewSession}
                onSelect={(id) => {
                  setActiveSessionId(id);
                  setLeftDrawer(false);
                }}
                onDelete={deleteSession}
                onExport={exportSession}
                onClose={() => setLeftDrawer(false)}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>

        <AnimatePresence>
          {rightDrawer ? (
            <motion.div
              className="drawer rightDrawer"
              initial={reduceMotion ? false : { x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: reduceMotion ? 0 : 0.24, ease: "easeOut" }}
            >
              <TracePanel
                tools={tools}
                metrics={latestMetrics}
                runStatus={currentStatus}
                model={latestAssistant?.run?.model ?? config?.model}
                copiedId={copiedId}
                onCopy={copyValue}
                onClose={() => setRightDrawer(false)}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </main>
    </Theme>
  );
}
