import { Columns2, FileCode2, GitCompareArrows } from "lucide-react";

export type EditorMode = "original" | "fixed" | "diff";

type EditorTabsProps = {
  mode: EditorMode;
  onModeChange: (mode: EditorMode) => void;
};

const tabs = [
  { mode: "original" as const, label: "original.code", icon: FileCode2 },
  { mode: "fixed" as const, label: "fixed.code", icon: Columns2 },
  { mode: "diff" as const, label: "attempt.diff", icon: GitCompareArrows },
];

export function EditorTabs({ mode, onModeChange }: EditorTabsProps) {
  return (
    <div className="flex h-10 items-end border-b border-[var(--line)] bg-[var(--panel-2)]">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.mode}
            onClick={() => onModeChange(tab.mode)}
            className={`flex h-10 items-center gap-2 border-r border-[var(--line)] px-3 text-sm ${
              mode === tab.mode ? "bg-[var(--panel)] text-white" : "text-[var(--muted)] hover:text-white"
            }`}
          >
            <Icon size={15} /> {tab.label}
          </button>
        );
      })}
    </div>
  );
}
