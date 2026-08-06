import {
  AIChatResponse,
  AIInsightResponse,
  ApiError,
  AuthResponse,
  ChatMessage,
  CompanyInfo,
  HistoryResponse,
  IndicatorsResponse,
  NewsArticleResponse,
  SocialPostResponse,
  SocialSource,
  StockSummary,
  TickerSearchResult,
  UserResponse,
  WatchlistItemResponse,
  WatchlistSummaryItem,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "ss_token";

// The auth token is kept in a module variable (set by the AuthProvider) with
// localStorage as the durable fallback, so every request picks it up without
// each caller having to thread it through.
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  }
}

function currentToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") return window.localStorage.getItem(TOKEN_KEY);
  return null;
}

type RequestOptions = RequestInit & { timeoutMs?: number };

async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const { timeoutMs, ...init } = options ?? {};
  let res: Response;
  // Local LLM calls can run long, so callers can pass a timeout; without one
  // we let the browser's default apply (used by all the fast data endpoints).
  const controller = timeoutMs ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const token = currentToken();
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller?.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch (err) {
    if (controller?.signal.aborted) {
      throw new ApiError(0, "The AI request timed out. The local model may still be warming up — try again.");
    }
    // Network failure (backend down, wrong URL, CORS block) - give a clear
    // message instead of letting a raw TypeError bubble up to the UI.
    throw new ApiError(0, "Could not reach the backend. Is it running?");
  } finally {
    if (timer) clearTimeout(timer);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON - fall back to statusText, already set above
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- Auth (Phase 11) ---
  login: (username: string, passphrase?: string) =>
    request<AuthResponse>(`/api/auth/login`, {
      method: "POST",
      body: JSON.stringify({ username, passphrase: passphrase || null }),
    }),

  getMe: () => request<UserResponse>(`/api/auth/me`),

  updatePreferences: (preferences: Record<string, unknown>) =>
    request<UserResponse>(`/api/auth/preferences`, {
      method: "PUT",
      body: JSON.stringify({ preferences }),
    }),

  searchTickers: (q: string) =>
    request<TickerSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(q)}`),

  getHistory: (symbol: string, period = "1y", interval = "1d") =>
    request<HistoryResponse>(
      `/api/stocks/${encodeURIComponent(symbol)}/history?period=${period}&interval=${interval}`
    ),

  getInfo: (symbol: string) => request<CompanyInfo>(`/api/stocks/${encodeURIComponent(symbol)}/info`),

  getIndicators: (symbol: string) =>
    request<IndicatorsResponse>(`/api/stocks/${encodeURIComponent(symbol)}/indicators`),

  getSummary: (symbol: string) =>
    request<StockSummary>(`/api/stocks/${encodeURIComponent(symbol)}/summary`),

  getNews: (symbol: string) => request<NewsArticleResponse[]>(`/api/news/${encodeURIComponent(symbol)}`),

  getWatchlist: () => request<WatchlistItemResponse[]>(`/api/watchlist`),

  addToWatchlist: (symbol: string) =>
    request<WatchlistItemResponse>(`/api/watchlist`, {
      method: "POST",
      body: JSON.stringify({ symbol }),
    }),

  removeFromWatchlist: (symbol: string) =>
    request<void>(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),

  getWatchlistSummary: () => request<WatchlistSummaryItem[]>(`/api/watchlist/summary`),

  getWatchlistNews: (limit = 20) => request<NewsArticleResponse[]>(`/api/watchlist/news?limit=${limit}`),

  getSocial: (symbol: string, source: SocialSource) =>
    request<SocialPostResponse[]>(`/api/social/${encodeURIComponent(symbol)}?source=${source}`),

  // Phase 10 - AI investment insight (RAG-grounded, via the local Ollama/Claude LLM).
  // The first insight after a fresh backend start is the slow one: it loads the
  // embedding model, rebuilds the KB (yfinance + news), and cold-loads the local
  // LLM - measured ~220s on an 8B model. Later calls are much faster (~50s), but
  // the timeout has to cover that worst-case cold start or the UI aborts a request
  // the backend is still working on.
  generateInsight: (symbol: string) =>
    request<AIInsightResponse>(`/api/ai-insight/${encodeURIComponent(symbol)}`, {
      method: "POST",
      timeoutMs: 300_000,
    }),

  chatInsight: (symbol: string, messages: ChatMessage[]) =>
    request<AIChatResponse>(`/api/ai-insight/${encodeURIComponent(symbol)}/chat`, {
      method: "POST",
      body: JSON.stringify({ messages }),
      timeoutMs: 240_000,
    }),
};
