"use client";
import { createContext, useContext } from "react";

export type SidebarContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  close: () => void;
};

// Default no-op value so Topbar is safe even if rendered outside AppShell.
export const SidebarContext = createContext<SidebarContextValue>({
  open: false,
  setOpen: () => {},
  toggle: () => {},
  close: () => {},
});

export function useSidebar(): SidebarContextValue {
  return useContext(SidebarContext);
}
