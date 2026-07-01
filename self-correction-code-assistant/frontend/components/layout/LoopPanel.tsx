import { GitBranch } from "lucide-react";
import type { CacheStats } from "@/lib/types/loop";

type LoopPanelProps = {
  cacheStats?: CacheStats;
  sessionId?: string;
};

export function LoopPanel({ cacheStats, sessionId }: LoopPanelProps) {
  return (
    <aside className="explorer-sidebar thin-scrollbar overflow-y-auto border-r bg-[var(--panel)]">
      <div className="border-b border-[var(--line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Loop Status
      </div>
      <div className="space-y-4 p-3">
        <div className="flex items-center gap-2 text-sm text-[var(--text)]">
          <GitBranch size={16} className="text-[var(--accent)]" />
          <span>{sessionId ? `Session: ${sessionId.slice(0, 8)}...` : "No active session"}</span>
        </div>

        {cacheStats && (
          <section className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Cache Stats</div>
            <div className="space-y-1 text-sm text-[var(--text)]">
              <StatRow label="Active sessions" value={cacheStats.active_sessions} />
              <StatRow label="Total checkpoints" value={cacheStats.total_checkpoints} />
              <StatRow label="Max size" value={cacheStats.max_size} />
              <StatRow label="TTL" value={`${cacheStats.ttl_seconds}s`} />
              <StatRow label="DB size" value={`${cacheStats.db_size_kb} KB`} />
            </div>
          </section>
        )}

        {!cacheStats && (
          <p className="text-xs text-[var(--muted)]">
            Cache stats will load when the backend is available.
          </p>
        )}
      </div>
    </aside>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded border border-[var(--line)] bg-[var(--panel-2)] px-3 py-2">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}
