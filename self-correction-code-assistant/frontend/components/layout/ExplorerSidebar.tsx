import { Bot, Play, RotateCcw } from "lucide-react";

import { FileUploader } from "@/components/editor/FileUploader";
import { SampleBugPicker } from "@/components/history/SampleBugPicker";
import type { Language, SampleBug } from "@/lib/types/loop";

type ExplorerSidebarProps = {
  samples: SampleBug[];
  selectedLanguage: Language;
  errorMessage: string;
  userContext: string;
  loading: boolean;
  useMultiAgent: boolean;
  onSampleSelect: (sample: SampleBug) => void;
  onLanguageChange: (language: Language) => void;
  onErrorMessageChange: (value: string) => void;
  onUserContextChange: (value: string) => void;
  onAnalyze: () => void;
  onReset: () => void;
  onFileUpload: (file: File) => void;
  onFolderUpload: (file: File) => void;
  onMultipleFilesUpload: (files: File[]) => void;
  onToggleMultiAgent: () => void;
};

const languages: Language[] = ["Python", "JavaScript", "TypeScript", "Java", "C++"];

export function ExplorerSidebar({
  samples,
  selectedLanguage,
  errorMessage,
  userContext,
  loading,
  useMultiAgent,
  onSampleSelect,
  onLanguageChange,
  onErrorMessageChange,
  onUserContextChange,
  onAnalyze,
  onReset,
  onFileUpload,
  onFolderUpload,
  onMultipleFilesUpload,
  onToggleMultiAgent,
}: ExplorerSidebarProps) {
  return (
    <aside className="explorer-sidebar thin-scrollbar overflow-y-auto border-r bg-[var(--panel)]">
      <div className="border-b border-[var(--line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Correction Workspace
      </div>
      <div className="space-y-4 p-3">
        <FileUploader
          loading={loading}
          onFileUpload={onFileUpload}
          onFolderUpload={onFolderUpload}
          onMultipleFilesUpload={onMultipleFilesUpload}
        />

        <SampleBugPicker samples={samples} onSelect={onSampleSelect} />

        <label className="block space-y-1.5 text-xs text-[var(--muted)]">
          Language
          <select
            value={selectedLanguage}
            onChange={(event) => onLanguageChange(event.target.value as Language)}
            className="w-full rounded border border-[var(--line)] bg-[var(--panel-2)] px-2 py-2 text-sm text-[var(--text)] outline-none"
          >
            {languages.map((language) => (
              <option key={language}>{language}</option>
            ))}
          </select>
        </label>

        <label className="block space-y-1.5 text-xs text-[var(--muted)]">
          Error or issue
          <textarea
            value={errorMessage}
            onChange={(event) => onErrorMessageChange(event.target.value)}
            rows={5}
            className="code-textarea thin-scrollbar w-full resize-none rounded px-2 py-2 text-sm"
            placeholder="Paste compiler error, runtime error, or issue description"
          />
        </label>

        <label className="block space-y-1.5 text-xs text-[var(--muted)]">
          Context
          <textarea
            value={userContext}
            onChange={(event) => onUserContextChange(event.target.value)}
            rows={4}
            className="code-textarea thin-scrollbar w-full resize-none rounded px-2 py-2 text-sm"
            placeholder="Optional project context"
          />
        </label>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onAnalyze}
            disabled={loading}
            className="flex items-center justify-center gap-2 rounded bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play size={15} /> Analyze
          </button>
          <button
            onClick={onReset}
            className="flex items-center justify-center gap-2 rounded border border-[var(--line)] px-3 py-2 text-sm text-[var(--text)] hover:bg-[var(--panel-3)]"
          >
            <RotateCcw size={15} /> Reset
          </button>
        </div>

        <div className="flex items-center justify-between rounded border border-[var(--line)] bg-[var(--panel-2)] px-3 py-2">
          <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <Bot size={14} className={useMultiAgent ? "text-[var(--accent)]" : ""} />
            Multi-Agent Mode
          </span>
          <button
            role="switch"
            aria-checked={useMultiAgent}
            onClick={onToggleMultiAgent}
            title={useMultiAgent ? "Disable multi-agent pipeline" : "Enable 4-agent pipeline (Analyzer → Fix → Reviewer → Tests)"}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              useMultiAgent ? "bg-[var(--accent)]" : "bg-[var(--panel-3)]"
            }`}
          >
            <span
              className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                useMultiAgent ? "translate-x-4.5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </div>
    </aside>
  );
}
