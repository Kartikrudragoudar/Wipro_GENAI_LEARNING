import { AlertTriangle, BrainCircuit, CheckCircle2, Copy, Sparkles, Terminal, XCircle } from "lucide-react";
import { useState } from "react";

import { CorrectionHistory } from "@/components/history/CorrectionHistory";
import type { AssistantResponse, CorrectionAttempt, ReviewVerdict, TestSuiteOutput } from "@/lib/types/loop";

type AssistantPanelProps = {
  response?: AssistantResponse;
  attempts: CorrectionAttempt[];
  selectedAttemptNumber?: number;
  loading: boolean;
  error?: string;
  onAttemptSelect: (attemptNumber: number) => void;
  onBranch?: (attemptNumber: number) => void;
  onCopyCode?: (code: string) => void;
  onDownloadCode?: (code: string, attemptNumber: number) => void;
  reviewerVerdict?: ReviewVerdict | null;
  testSuite?: TestSuiteOutput | null;
  toolCallsTrace?: string[];
};

export function AssistantPanel({
  response,
  attempts,
  selectedAttemptNumber,
  loading,
  error,
  onAttemptSelect,
  onBranch,
  onCopyCode,
  onDownloadCode,
  reviewerVerdict,
  testSuite,
  toolCallsTrace,
}: AssistantPanelProps) {
  const activeAttempt = attempts.find((attempt) => attempt.attempt_number === selectedAttemptNumber);

  return (
    <aside className="assistant-panel thin-scrollbar overflow-y-auto border-l bg-[var(--panel)]">
      <div className="border-b border-[var(--line)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Assistant Loop
      </div>
      <div className="space-y-4 p-4">
        {loading && <StateNotice icon={<Sparkles size={16} />} text="Loop is processing the current step..." />}
        {error && <StateNotice danger icon={<AlertTriangle size={16} />} text={error} />}
        {!response && !loading && <StateNotice icon={<BrainCircuit size={16} />} text="Select a sample or paste code, then run Analyze." />}

        {response && (
          <section className="space-y-3">
            <Metric confidence={activeAttempt?.confidence_score ?? response.confidence_score} />
            <InfoBlock title="Bug summary" value={activeAttempt?.bug_summary ?? response.bug_summary} />
            <InfoBlock title="Root cause" value={activeAttempt?.root_cause ?? response.root_cause} />
            <CopyableInfoBlock title="Explanation" value={activeAttempt?.explanation ?? response.explanation} />
            <InfoList title="Suggested tests" values={response.suggested_tests} icon={<CheckCircle2 size={14} />} />
            <InfoList title="Risks" values={response.risks} icon={<AlertTriangle size={14} />} />
          </section>
        )}

        {reviewerVerdict && <ReviewerVerdictBlock verdict={reviewerVerdict} />}
        {testSuite && <TestSuiteBlock suite={testSuite} />}
        {toolCallsTrace && toolCallsTrace.length > 0 && <ToolCallsTrace calls={toolCallsTrace} />}

        <CorrectionHistory
          attempts={attempts}
          selectedAttemptNumber={selectedAttemptNumber}
          onSelect={onAttemptSelect}
          onBranch={onBranch}
          onCopyCode={onCopyCode}
          onDownloadCode={onDownloadCode}
        />
      </div>
    </aside>
  );
}

function Metric({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100);
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-2 flex items-center justify-between text-xs text-[var(--muted)]">
        <span>Confidence</span>
        <span>{percent}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-[#263241]">
        <div className="h-full bg-[var(--accent-2)]" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function InfoBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{title}</div>
      <p className="text-sm leading-6 text-[var(--text)]">{value}</p>
    </div>
  );
}

function CopyableInfoBlock({ title, value }: { title: string; value: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{title}</span>
        <button
          onClick={handleCopy}
          title="Copy to clipboard"
          aria-label={`Copy ${title}`}
          className="grid h-6 w-6 place-items-center rounded text-[var(--muted)] hover:text-white"
        >
          <Copy size={12} />
        </button>
      </div>
      <p className="text-sm leading-6 text-[var(--text)]">{value}</p>
      {copied && <span className="mt-1 block text-xs text-[var(--accent-2)]">Copied!</span>}
    </div>
  );
}

function InfoList({ title, values, icon }: { title: string; values: string[]; icon: React.ReactNode }) {
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{title}</div>
      <div className="space-y-2">
        {values.map((value) => (
          <div key={value} className="flex gap-2 text-sm text-[var(--text)]">
            <span className="mt-1 text-[var(--accent)]">{icon}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StateNotice({ icon, text, danger = false }: { icon: React.ReactNode; text: string; danger?: boolean }) {
  return (
    <div className={`flex items-center gap-2 rounded border px-3 py-2 text-sm ${danger ? "border-[var(--danger)] text-[var(--danger)]" : "border-[var(--line)] text-[var(--muted)]"}`}>
      {icon} {text}
    </div>
  );
}

function ReviewerVerdictBlock({ verdict }: { verdict: ReviewVerdict }) {
  const passed = verdict.passed;
  return (
    <div className={`rounded border p-3 ${passed ? "border-green-700 bg-green-950/40" : "border-red-700 bg-red-950/40"}`}>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Reviewer Verdict</span>
        <span className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-bold ${passed ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
          {passed ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
          {verdict.recommendation.toUpperCase()}
        </span>
      </div>
      <div className="mb-1 text-xs text-[var(--muted)]">
        Confidence: {Math.round(verdict.reviewer_confidence * 100)}%
      </div>
      {verdict.issues.length > 0 && (
        <ul className="mt-2 space-y-1">
          {verdict.issues.map((issue, i) => (
            <li key={i} className="flex gap-2 text-xs text-red-300">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              <span>{issue}</span>
            </li>
          ))}
        </ul>
      )}
      {verdict.lint_output && (
        <pre className="mt-2 rounded bg-black/30 p-2 text-xs text-yellow-300 whitespace-pre-wrap">{verdict.lint_output}</pre>
      )}
    </div>
  );
}

function TestSuiteBlock({ suite }: { suite: TestSuiteOutput }) {
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Suggested Test Suite</div>
      <p className="mb-2 text-xs italic text-[var(--muted)]">{suite.test_strategy}</p>
      <ul className="space-y-1">
        {suite.tests.map((t, i) => (
          <li key={i} className="flex gap-2 text-sm text-[var(--text)]">
            <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[var(--accent)]" />
            <span>{t}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-[var(--muted)]">{suite.coverage_notes}</p>
    </div>
  );
}

function ToolCallsTrace({ calls }: { calls: string[] }) {
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--panel-2)] p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Terminal size={12} /> Tool calls
      </div>
      <ol className="space-y-1">
        {calls.map((call, i) => (
          <li key={i} className="flex items-center gap-2 text-xs text-[var(--text)]">
            <span className="shrink-0 text-[var(--muted)]">{i + 1}.</span>
            <code className="rounded bg-[var(--panel)] px-1 py-0.5 font-mono text-[var(--accent-2)]">{call}</code>
          </li>
        ))}
      </ol>
    </div>
  );
}
