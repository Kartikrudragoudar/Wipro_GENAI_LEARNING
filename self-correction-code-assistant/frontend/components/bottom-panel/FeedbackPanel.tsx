import { RefreshCcw } from "lucide-react";

type FeedbackPanelProps = {
  value: string;
  loading: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
  onSelfCorrect: () => void;
};

export function FeedbackPanel({ value, loading, disabled, onChange, onSelfCorrect }: FeedbackPanelProps) {
  return (
    <div className="grid h-full grid-cols-[1fr_auto] gap-3 p-3">
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="code-textarea thin-scrollbar h-full resize-none rounded px-3 py-2 text-sm"
        placeholder="Paste test output, compiler error, runtime error, or reviewer feedback here. The MVP never executes submitted code."
      />
      <button
        onClick={onSelfCorrect}
        disabled={disabled || loading}
        className="flex h-10 items-center gap-2 self-end rounded bg-[var(--accent-2)] px-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <RefreshCcw size={15} /> Self-correct
      </button>
    </div>
  );
}
