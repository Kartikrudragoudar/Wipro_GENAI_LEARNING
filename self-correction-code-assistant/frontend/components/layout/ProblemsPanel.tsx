import { AlertCircle, CheckCircle2 } from "lucide-react";

type ProblemsPanelProps = {
  error?: string;
  logs: string[];
};

export function ProblemsPanel({ error, logs }: ProblemsPanelProps) {
  const errorLogs = logs.filter((l) => l.toLowerCase().includes("failed") || l.toLowerCase().includes("error"));

  return (
    <aside className="explorer-sidebar thin-scrollbar overflow-y-auto border-r bg-[var(--panel)]">
      <div className="border-b border-[var(--line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Problems
      </div>
      <div className="space-y-3 p-3">
        {error && (
          <div className="flex items-start gap-2 rounded border border-[var(--danger)] bg-[var(--panel-2)] p-3 text-sm text-[var(--danger)]">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!error && errorLogs.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-[var(--accent-2)]">
            <CheckCircle2 size={16} />
            <span>No problems detected.</span>
          </div>
        )}

        {errorLogs.length > 0 && (
          <section className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Recent errors</div>
            {errorLogs.slice(0, 10).map((log, i) => (
              <div key={i} className="flex items-start gap-2 rounded border border-[var(--line)] bg-[var(--panel-2)] p-2 text-xs text-[var(--warn)]">
                <AlertCircle size={12} className="mt-0.5 shrink-0" />
                <span>{log}</span>
              </div>
            ))}
          </section>
        )}
      </div>
    </aside>
  );
}
