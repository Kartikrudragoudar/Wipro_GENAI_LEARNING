import { AlertCircle, ClipboardCheck, ListTree, ScrollText, TerminalSquare } from "lucide-react";
import { useState } from "react";

import { FeedbackPanel } from "@/components/bottom-panel/FeedbackPanel";
import { LoopTracePanel } from "@/components/bottom-panel/LoopTracePanel";
import type { LoopTrace } from "@/lib/types/loop";

type BottomTab = "Problems" | "Tests" | "Output" | "Logs" | "Loop Trace";

type BottomPanelProps = {
  feedback: string;
  loading: boolean;
  canSelfCorrect: boolean;
  error?: string;
  suggestedTests: string[];
  trace?: LoopTrace;
  logs: string[];
  onFeedbackChange: (value: string) => void;
  onSelfCorrect: () => void;
};

const tabs: Array<{ label: BottomTab; icon: React.ReactNode }> = [
  { label: "Problems", icon: <AlertCircle size={14} /> },
  { label: "Tests", icon: <ClipboardCheck size={14} /> },
  { label: "Output", icon: <TerminalSquare size={14} /> },
  { label: "Logs", icon: <ScrollText size={14} /> },
  { label: "Loop Trace", icon: <ListTree size={14} /> },
];

export function BottomPanel({
  feedback,
  loading,
  canSelfCorrect,
  error,
  suggestedTests,
  trace,
  logs,
  onFeedbackChange,
  onSelfCorrect,
}: BottomPanelProps) {
  const [activeTab, setActiveTab] = useState<BottomTab>("Tests");

  return (
    <section className="bottom-panel h-[230px] border-t bg-[var(--panel)]">
      <div className="flex h-9 items-center border-b border-[var(--line)] bg-[var(--panel-2)]">
        {tabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setActiveTab(tab.label)}
            className={`flex h-full items-center gap-1.5 border-r border-[var(--line)] px-3 text-xs ${
              activeTab === tab.label ? "bg-[var(--panel)] text-white" : "text-[var(--muted)] hover:text-white"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      <div className="h-[calc(100%-36px)]">
        {activeTab === "Problems" && <TextPanel lines={error ? [error] : ["No active UI or API errors."]} tone={error ? "danger" : "muted"} />}
        {activeTab === "Tests" && (
          <FeedbackPanel value={feedback} loading={loading} disabled={!canSelfCorrect} onChange={onFeedbackChange} onSelfCorrect={onSelfCorrect} />
        )}
        {activeTab === "Output" && <TextPanel lines={suggestedTests.length ? suggestedTests : ["Suggested tests appear after a correction is generated."]} />}
        {activeTab === "Logs" && <TextPanel lines={logs.length ? logs : ["Loop events will appear here."]} />}
        {activeTab === "Loop Trace" && <LoopTracePanel trace={trace} />}
      </div>
    </section>
  );
}

function TextPanel({ lines, tone = "normal" }: { lines: string[]; tone?: "normal" | "muted" | "danger" }) {
  const color = tone === "danger" ? "text-[var(--danger)]" : tone === "muted" ? "text-[var(--muted)]" : "text-[var(--text)]";
  return (
    <div className={`thin-scrollbar h-full overflow-auto p-3 font-mono text-sm leading-6 ${color}`}>
      {lines.map((line, index) => (
        <div key={`${line}-${index}`}>{line}</div>
      ))}
    </div>
  );
}
