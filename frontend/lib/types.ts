export interface TickerSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  region: string;
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryResponse {
  symbol: string;
  period: string;
  interval: string;
  candles: PricePoint[];
}

export interface CompanyInfo {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  currency: string | null;
}

export interface IndicatorsResponse {
  symbol: string;
  current_price: number | null;
  ema50: number | null;
  ema200: number | null;
  trend_signal: "bullish" | "bearish" | null;
  golden_cross: boolean | null;
}

export interface StockSummary {
  symbol: string;
  company: CompanyInfo;
  indicators: IndicatorsResponse;
}

export interface WatchlistItemResponse {
  id: number;
  symbol: string;
  added_at: string;
}

export interface NewsArticleResponse {
  id: number;
  symbol: string;
  title: string;
  url: string;
  source: string | null;
  published_at: string | null;
  sentiment_score: number | null;
  sentiment_label: "positive" | "negative" | "neutral" | null;
  keywords: string[] | null;
}

export interface WatchlistSummaryItem {
  symbol: string;
  summary: StockSummary | null;
  error: string | null;
}

export type SocialSource = "reddit" | "stocktwits";

export interface SocialPostResponse {
  id: number;
  symbol: string;
  source: SocialSource;
  author: string | null;
  content: string;
  url: string;
  score: number | null;
  posted_at: string | null;
  sentiment_score: number | null;
  sentiment_label: "positive" | "negative" | "neutral" | null;
  keywords: string[] | null;
}

export interface AuthResponse {
  token: string;
  username: string;
  has_passphrase: boolean;
  is_new: boolean;
}

export interface UserResponse {
  username: string;
  has_passphrase: boolean;
  preferences: Record<string, unknown>;
}

export interface AIInsightSource {
  doc_type: string | null;
  text: string;
}

export interface AIInsightResponse {
  symbol: string;
  provider: string;
  insight: string;
  sources: AIInsightSource[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AIChatResponse {
  symbol: string;
  provider: string;
  reply: string;
  sources: AIInsightSource[];
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
