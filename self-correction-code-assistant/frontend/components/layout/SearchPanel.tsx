import { Search } from "lucide-react";

export function SearchPanel() {
  return (
    <aside className="explorer-sidebar thin-scrollbar overflow-y-auto border-r bg-[var(--panel)]">
      <div className="border-b border-[var(--line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Search
      </div>
      <div className="flex flex-col items-center gap-3 p-6 text-center">
        <Search size={24} className="text-[var(--muted)]" />
        <p className="text-sm text-[var(--muted)]">
          Search across sessions and correction history.
        </p>
        <p className="text-xs text-[var(--muted)]">Coming soon — session history search will query the backend cache.</p>
      </div>
    </aside>
  );
}
