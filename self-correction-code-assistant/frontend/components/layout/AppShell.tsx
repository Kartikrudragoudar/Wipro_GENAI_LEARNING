import type { ReactNode } from "react";

import { ActivityBar } from "@/components/layout/ActivityBar";
import { StatusBar } from "@/components/layout/StatusBar";
import type { LoopStatus, SidebarView, Theme } from "@/lib/types/loop";

type AppShellProps = {
  explorer: ReactNode;
  searchPanel: ReactNode;
  loopPanel: ReactNode;
  problemsPanel: ReactNode;
  editor: ReactNode;
  assistant: ReactNode;
  status: LoopStatus;
  sessionId?: string;
  attemptCount: number;
  activeView: SidebarView;
  theme: Theme;
  onViewChange: (view: SidebarView) => void;
  onThemeToggle: () => void;
};

export function AppShell({
  explorer,
  searchPanel,
  loopPanel,
  problemsPanel,
  editor,
  assistant,
  status,
  sessionId,
  attemptCount,
  activeView,
  theme,
  onViewChange,
  onThemeToggle,
}: AppShellProps) {
  const sidebar = {
    explorer,
    search: searchPanel,
    loop: loopPanel,
    problems: problemsPanel,
  }[activeView];

  return (
    <main className="workspace-grid">
      <ActivityBar activeView={activeView} theme={theme} onViewChange={onViewChange} onThemeToggle={onThemeToggle} />
      {sidebar}
      {editor}
      {assistant}
      <StatusBar status={status} sessionId={sessionId} attemptCount={attemptCount} />
    </main>
  );
}
