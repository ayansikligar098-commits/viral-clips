import Link from "next/link";

export default function EmptyState({
  title,
  message,
  actionHref,
  actionLabel,
}: {
  title: string;
  message: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/15 bg-panel p-6 sm:p-10 text-center">
      <p className="text-lg font-semibold text-white">{title}</p>
      <p className="text-slate-400 mt-2 max-w-md mx-auto">{message}</p>
      {actionHref && actionLabel && (
        <Link href={actionHref} className="inline-flex min-h-[44px] items-center mt-5 px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium">
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
