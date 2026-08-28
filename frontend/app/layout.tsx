import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { DemoBanner, Footer, Header } from "@/components/chrome";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: {
    default: "BIS AI Assistant — Indian Standards & BIS Services",
    template: "%s · BIS AI Assistant",
  },
  description:
    "AI decision support for Indian Standards and BIS services. Find applicable standards, understand certification, locate testing laboratories and get source-verified answers.",
};

export const viewport: Viewport = {
  themeColor: "#0f2a4d",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="flex min-h-screen flex-col">
        <I18nProvider>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-ink-900 focus:px-4 focus:py-2 focus:text-sm focus:text-white"
          >
            Skip to content
          </a>
          <DemoBanner />
          <Header />
          <main id="main" className="flex-1">
            {children}
          </main>
          <Footer />
        </I18nProvider>
      </body>
    </html>
  );
}
