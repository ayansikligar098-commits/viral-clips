"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import { API_URL, getMe } from "@/lib/api";
import type { User } from "@/lib/types";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe().then(setUser).catch((err) => setError(err instanceof Error ? err.message : "Not signed in."));
  }, []);

  return (
    <>
      <Topbar title="Settings" />
      <main className="p-4 sm:p-6 space-y-5 max-w-2xl w-full min-w-0">
        <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
          <h3 className="font-semibold text-white mb-2">Account</h3>
          {error && <p className="text-sm text-slate-400">{error} Sign in to see your account info.</p>}
          {user && (
            <dl className="text-sm space-y-1">
              <div className="flex flex-col sm:flex-row sm:justify-between gap-1"><dt className="text-slate-400">Email</dt><dd className="text-white break-all">{user.email}</dd></div>
              {user.name && <div className="flex flex-col sm:flex-row sm:justify-between gap-1"><dt className="text-slate-400">Name</dt><dd className="text-white break-words">{user.name}</dd></div>}
              {user.created_at && <div className="flex flex-col sm:flex-row sm:justify-between gap-1"><dt className="text-slate-400">Joined</dt><dd className="text-white">{new Date(user.created_at).toLocaleDateString()}</dd></div>}
            </dl>
          )}
        </section>
        <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
          <h3 className="font-semibold text-white mb-2">API</h3>
          <p className="text-sm text-slate-300 break-words">Backend API URL: <code className="text-violet-300 break-all">{API_URL}</code></p>
          <p className="text-xs text-slate-500 mt-1">Set via NEXT_PUBLIC_API_URL (see .env.example). No secrets are stored in this frontend.</p>
        </section>
        <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
          <h3 className="font-semibold text-white mb-2">Subscription</h3>
          <p className="text-sm text-slate-300">
            The architecture is Stripe-ready (plans table, usage quotas and a webhook stub are part of the
            Phase 3 backend design in ARCHITECTURE.md), but billing is not live in Phase 1 — there is no
            fake checkout or fake plan shown here.
          </p>
        </section>
      </main>
    </>
  );
}
