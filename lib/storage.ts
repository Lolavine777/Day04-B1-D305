import type { ChatSession } from "@/lib/types";

const STORAGE_KEY = "fieldwork.chat.sessions.v1";
const ACTIVE_KEY = "fieldwork.chat.active-session.v1";
const THEME_KEY = "fieldwork.theme.v1";

export function createSession(): ChatSession {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "New research",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export function loadSessions(): ChatSession[] {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (!value) {
      return [];
    }
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (session): session is ChatSession =>
        typeof session?.id === "string" &&
        typeof session?.title === "string" &&
        Array.isArray(session?.messages),
    );
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function loadActiveSessionId(): string | null {
  return localStorage.getItem(ACTIVE_KEY);
}

export function saveActiveSessionId(sessionId: string): void {
  localStorage.setItem(ACTIVE_KEY, sessionId);
}

export function loadTheme(): "light" | "dark" {
  return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
}

export function saveTheme(theme: "light" | "dark"): void {
  localStorage.setItem(THEME_KEY, theme);
}
