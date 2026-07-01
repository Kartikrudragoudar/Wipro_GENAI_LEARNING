import { Clock3, Copy, Download, GitBranch } from "lucide-react";

import type { CorrectionAttempt } from "@/lib/types/loop";

type CorrectionHistoryProps = {
  attempts: CorrectionAttempt[];
  selectedAttemptNumber?: number;
  onSelect: (attemptNumber: number) => void;
  onBranch?: (attemptNumber: number) => void;
  onCopyCode?: (code: string) => void;
  onDownloadCode?: (code: string, attemptNumber: number) => void;
};

export function CorrectionHistory({
  attempts,
  selectedAttemptNumber,
  onSelect,
  onBranch,
  onCopyCode,
  onDownloadCode,
}: CorrectionHistoryProps) {
  return (
    <section className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Correction History</div>
      {attempts.length === 0 && (
        <div className="rounded border border-dashed border-[var(--line)] p-3 text-sm text-[var(--muted)]">
          Attempts will appear here after the analysis loop runs.
        </div>
      )}
      <div className="space-y-2">
        {attempts.map((attempt) => (
          <div
            key={attempt.attempt_number}
            className={`rounded border transition ${
              selectedAttemptNumber === attempt.attempt_number
                ? "border-[var(--accent)] bg-[#102334]"
                : "border-[var(--line)] bg-[var(--panel-2)] hover:bg-[var(--panel-3)]"
            }`}
          >
            <button
              onClick={() => onSelect(attempt.attempt_number)}
              className="w-full p-3 text-left"
            >
              <div className="flex items-center justify-between text-sm font-semibold">
                <span>Attempt {attempt.attempt_number}</span>
                <span className="rounded bg-[#263241] px-2 py-0.5 text-xs text-[var(--accent-2)]">{attempt.status}</span>
              </div>
              <div className="mt-2 flex items-center gap-1.5 text-xs text-[var(--muted)]">
                <Clock3 size={13} /> {new Date(attempt.timestamp).toLocaleString()}
              </div>
              <p className="mt-2 text-sm leading-5 text-[var(--text)]">{attempt.change_summary}</p>
            </button>
            <div className="flex items-center gap-1 border-t border-[var(--line)] px-3 py-1.5">
              {onCopyCode && (
                <button
                  onClick={() => onCopyCode(attempt.fixed_code)}
                  title="Copy fixed code"
                  aria-label="Copy fixed code"
                  className="grid h-7 w-7 place-items-center rounded text-[var(--muted)] hover:bg-[var(--panel-3)] hover:text-white"
                >
                  <Copy size={14} />
                </button>
              )}
              {onDownloadCode && (
                <button
                  onClick={() => onDownloadCode(attempt.fixed_code, attempt.attempt_number)}
                  title="Download fixed code"
                  aria-label="Download fixed code"
                  className="grid h-7 w-7 place-items-center rounded text-[var(--muted)] hover:bg-[var(--panel-3)] hover:text-white"
                >
                  <Download size={14} />
                </button>
              )}
              {onBranch && (
                <button
                  onClick={() => onBranch(attempt.attempt_number)}
                  title="Branch from this attempt"
                  aria-label="Branch from this attempt"
                  className="ml-auto flex items-center gap-1 rounded px-2 py-1 text-xs text-[var(--muted)] hover:bg-[var(--panel-3)] hover:text-white"
                >
                  <GitBranch size={13} /> Branch
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
