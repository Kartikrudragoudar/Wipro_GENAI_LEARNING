import { Bug, Code2, GitBranch, Search, Settings, Moon, Sun } from "lucide-react";

import type { SidebarView, Theme } from "@/lib/types/loop";

type ActivityBarProps = {
  activeView: SidebarView;
  theme: Theme;
  onViewChange: (view: SidebarView) => void;
  onThemeToggle: () => void;
};

const items: Array<{ view: SidebarView; label: string; icon: typeof Code2 }> = [
  { view: "explorer", label: "Explorer", icon: Code2 },
  { view: "search", label: "Search", icon: Search },
  { view: "loop", label: "Loop", icon: GitBranch },
  { view: "problems", label: "Problems", icon: Bug },
];

export function ActivityBar({ activeView, theme, onViewChange, onThemeToggle }: ActivityBarProps) {
  return (
    <aside className="activity-bar flex flex-col items-center justify-between py-3">
      <div className="flex flex-col gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.view}
              title={item.label}
              aria-label={item.label}
              onClick={() => onViewChange(item.view)}
              className={`grid h-9 w-9 place-items-center border-l-2 transition ${
                activeView === item.view ? "border-[var(--accent)] text-white" : "border-transparent text-[var(--muted)] hover:text-white"
              }`}
            >
              <Icon size={20} />
            </button>
          );
        })}
      </div>
      <div className="flex flex-col gap-3">
        <button
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          aria-label="Toggle theme"
          onClick={onThemeToggle}
          className="grid h-9 w-9 place-items-center text-[var(--muted)] hover:text-white"
        >
          {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <button title="Settings" aria-label="Settings" className="grid h-9 w-9 place-items-center text-[var(--muted)] hover:text-white">
          <Settings size={20} />
        </button>
      </div>
    </aside>
  );
}
