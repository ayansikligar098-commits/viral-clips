import type { Metadata, Viewport } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Viral Clips — AI Viral Clipping Automation",
  description: "Turn long videos into a few strong 9:16 clips, scored and quality-gated, ready for Instagram Reels.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-ink text-slate-200 antialiased overflow-x-hidden">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
