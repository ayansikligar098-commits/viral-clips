"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import EmptyState from "@/components/EmptyState";
import { disconnectInstagram, instagramConnectUrl, listInstagramAccounts } from "@/lib/api";
import type { InstagramAccount } from "@/lib/types";

export default function InstagramPage() {
  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    listInstagramAccounts()
      .then(setAccounts)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load Instagram accounts."))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function disconnect(id: string | number) {
    if (!confirm("Disconnect this Instagram account?")) return;
    try { await disconnectInstagram(id); load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Disconnect failed."); }
  }

  return (
    <>
      <Topbar title="Instagram Accounts" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm max-w-2xl">
          Connect a Professional Instagram account via the official Meta Graph API. Publishing is
          always approval-gated — connecting an account never publishes anything on its own.
        </p>
        <a href={instagramConnectUrl()} className="inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium">
          Connect Instagram account
        </a>
        {loading && <p className="text-slate-400">Loading accounts…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && accounts.length === 0 && (
          <EmptyState title="No Instagram accounts connected" message="Connect an account above to publish or schedule approved clips to Reels." />
        )}
        <div className="space-y-3">
          {accounts.map((a) => (
            <div key={String(a.id)} className="rounded-2xl border border-white/10 bg-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium text-white break-words">{a.username ?? `Account ${String(a.id)}`}</p>
                <p className="text-xs text-slate-400 mt-1">{a.account_type ?? ""}{a.created_at ? ` · Connected ${new Date(a.created_at).toLocaleDateString()}` : ""}</p>
              </div>
              <button onClick={() => disconnect(a.id)} className="inline-flex min-h-[44px] items-center justify-center px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm">Disconnect</button>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
