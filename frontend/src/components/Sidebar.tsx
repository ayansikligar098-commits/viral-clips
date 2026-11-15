"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/upload", label: "Upload Video" },
  { href: "/analysis", label: "Video Analysis" },
  { href: "/clips", label: "Generated Clips" },
  { href: "/scores", label: "Viral Score" },
  { href: "/instagram", label: "Instagram Accounts" },
  { href: "/calendar", label: "Publishing Calendar" },
  { href: "/analytics", label: "Analytics" },
  { href: "/history", label: "Project History" },
  { href: "/settings", label: "Settings" },
];

export default function Sidebar({
  open = false,
  onClose,
}: {
  open?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();
  return (
    <aside
      aria-label="Main navigation"
      className={`fixed inset-y-0 left-0 z-50 w-60 max-w-[85vw] bg-panel border-r border-white/10 flex flex-col transition-transform duration-200 ease-in-out ${
        open ? "translate-x-0" : "-translate-x-full"
      } lg:translate-x-0`}
    >
      <div className="flex items-start justify-between gap-2 px-5 py-5">
        <div className="min-w-0">
          <Link href="/" onClick={onClose} className="text-lg font-bold text-white">
            ✂️ Viral<span className="text-violet-400">Clips</span>
          </Link>
          <p className="text-xs text-slate-400 mt-1">Fewer, better clips. 3–5 strong clips per video.</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close menu"
          className="lg:hidden inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 text-white"
        >
          <span aria-hidden="true" className="text-xl leading-none">✕</span>
        </button>
      </div>
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto pb-4">
        {NAV.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-[44px] items-center px-3 py-2 rounded-lg text-sm ${
                active ? "bg-violet-600/20 text-violet-200 font-medium" : "text-slate-300 hover:bg-white/5"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 text-xs text-slate-500">
        Quality over quantity — every clip must pass the quality gate.
      </div>
    </aside>
  );
}
