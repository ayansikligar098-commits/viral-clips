"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null); setBusy(true);
    try { await login(email, password); router.push("/"); }
    catch (err) { setError(err instanceof Error ? err.message : "Login failed."); }
    finally { setBusy(false); }
  }

  return (
    <main className="p-4 sm:p-6 flex justify-center min-w-0">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-white/10 bg-panel p-4 sm:p-6 space-y-4 mt-6 sm:mt-10">
        <h1 className="text-xl font-bold text-white">Log in</h1>
        <div>
          <label className="block text-sm text-slate-300 mb-1">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
        </div>
        <div>
          <label className="block text-sm text-slate-300 mb-1">Password</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
        </div>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button disabled={busy} className="w-full min-h-[44px] px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium disabled:opacity-50">{busy ? "Logging in…" : "Log in"}</button>
        <p className="text-sm text-slate-400">No account? <Link href="/register" className="text-violet-300">Register</Link></p>
      </form>
    </main>
  );
}
