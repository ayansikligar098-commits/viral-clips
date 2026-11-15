"use client";
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { SidebarContext } from "@/components/sidebar-context";

// Client shell: owns the mobile sidebar (drawer) open state and renders the
// sidebar + overlay + content wrapper. Desktop (lg+) keeps the static
// sidebar via `lg:pl-60` on the content wrapper only — no fixed padding
// on phones, so content is never squeezed under the sidebar.
export default function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close the drawer whenever the route changes (incl. nav-link taps).
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Prevent the page behind the drawer from scrolling while it is open.
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open ]);

  const toggle = useCallback(() => setOpen((o) => !o), []);
  const close = useCallback(() => setOpen(false), []);

  return (
    <SidebarContext.Provider value={{ open, setOpen, toggle, close }}>
      <Sidebar open={open} onClose={close} />
      {open && (
        <div
          aria-hidden="true"
          onClick={close}
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
        />
      )}
      <div className="min-h-screen min-w-0 flex flex-col lg:pl-60">{children}</div>
    </SidebarContext.Provider>
  );
}
