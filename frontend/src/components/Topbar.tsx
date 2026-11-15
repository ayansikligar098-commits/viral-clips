"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL, clearToken, getMe, isLoggedIn } from "@/lib/api";
import { useSidebar } from "@/components/sidebar-context";

export default function Topbar({ title }: { title: string }) {
  const [email, setEmail] = useState<string | null>(null);
  const { open, toggle } = useSidebar();
  useEffect(() => {
    if (!isLoggedIn()) return;
    getMe().then((u) => setEmail(u.email)).catch(() => setEmail(null));
  }, []);
  return (
    <header className="flex items-center gap-2 px-4 py-3 sm:px-6 sm:py-4 border-b border-white/10 bg-ink/80 sticky top-0 z-30">
      <button
        type="button"
        onClick={toggle}
        aria-label="Open menu"
        aria-expanded={open}
        className="lg:hidden inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 text-white"
      >
        <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="4" y1="7" x2="20" y2="7" />
          <line x1="4" y1="12" x2="20" y2="12" />
          <line x1="4" y1="17" x2="20" y2="17" />
        </svg>
      </button>
      <h1 className="min-w-0 flex-1 truncate text-lg sm:text-xl font-semibold text-white">{title}</h1>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3 text-sm">
        <span className="text-slate-400 hidden sm:inline truncate max-w-40">{API_URL}</span>
        {email ? (
          <>
            <span className="text-slate-300 hidden md:inline truncate max-w-40">{email}</span>
            <button
              onClick={() => { clearToken(); window.location.href = "/login"; }}
              className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white whitespace-nowrap"
            >
              Log out
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white whitespace-nowrap">Log in</Link>
            <Link href="/register" className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white whitespace-nowrap">Sign up</Link>
          </>
        )}
      </div>
    </header>
  );
}
