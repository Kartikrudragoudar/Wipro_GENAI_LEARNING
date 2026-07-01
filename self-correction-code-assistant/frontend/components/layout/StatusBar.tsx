import { CheckCircle2, GitBranch } from "lucide-react";

import type { LoopStatus } from "@/lib/types/loop";

const statusLabels: Record<LoopStatus, string> = {
  waiting_for_input: "Waiting for input",
  analyzing: "Analyzing",
  fix_generated: "Fix generated",
  awaiting_validation_feedback: "Awaiting validation feedback",
  self_correcting: "Self-correcting",
  correction_complete: "Correction complete",
  needs_another_loop: "Needs another loop",
};

type StatusBarProps = {
  status: LoopStatus;
  sessionId?: string;
  attemptCount: number;
};

export function StatusBar({ status, sessionId, attemptCount }: StatusBarProps) {
  return (
    <footer className="status-bar flex items-center justify-between px-3 text-xs text-white">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <GitBranch size={14} /> Loop status: {statusLabels[status]}
        </span>
        <span>Attempts: {attemptCount}</span>
      </div>
      <span className="flex items-center gap-1.5 text-white/90">
        <CheckCircle2 size={14} /> {sessionId ? `Session ${sessionId.slice(0, 8)}` : "No active session"}
      </span>
    </footer>
  );
}
