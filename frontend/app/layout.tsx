import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";
import { AuthProvider } from "@/lib/auth";

const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-display",
});
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "TickerBoom — AI Stock Screener",
  description: "Search stocks, read the chart, and get AI-generated insight grounded in fundamentals, trend, and news.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <AuthProvider>
          <NavBar />
          <main className="min-h-[calc(100vh-56px)] pb-16 sm:pb-0">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
