import { CheckCircle2, Circle } from "lucide-react";

import type { LoopTrace } from "@/lib/types/loop";

type LoopTracePanelProps = {
  trace?: LoopTrace;
};

export function LoopTracePanel({ trace }: LoopTracePanelProps) {
  const steps = [
    ["Input received", trace?.input_received],
    ["Analysis completed", trace?.analysis_completed],
    ["Correction generated", trace?.correction_generated],
    ["Validation feedback received", trace?.validation_feedback_received],
    ["Self-correction completed", trace?.self_correction_completed],
  ] as const;

  return (
    <div className="grid h-full grid-cols-[1fr_220px] gap-4 p-3 text-sm">
      <div className="grid grid-cols-5 gap-2">
        {steps.map(([label, done]) => (
          <div key={label} className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
            <div className={done ? "text-[var(--accent-2)]" : "text-[var(--muted)]"}>{done ? <CheckCircle2 size={18} /> : <Circle size={18} />}</div>
            <div className="mt-2 leading-5 text-[var(--text)]">{label}</div>
          </div>
        ))}
      </div>
      <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Final status</div>
        <div className="mt-2 text-base text-white">{trace?.final_status ?? "waiting_for_input"}</div>
      </div>
    </div>
  );
}
