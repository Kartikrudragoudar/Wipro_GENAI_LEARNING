"use client";

import { useCallback, useEffect, useState } from "react";

import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { BottomPanel } from "@/components/bottom-panel/BottomPanel";
import { CodeEditor } from "@/components/editor/CodeEditor";
import { DiffViewer } from "@/components/editor/DiffViewer";
import { EditorTabs } from "@/components/editor/EditorTabs";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { ExplorerSidebar } from "@/components/layout/ExplorerSidebar";
import { LoopPanel } from "@/components/layout/LoopPanel";
import { ProblemsPanel } from "@/components/layout/ProblemsPanel";
import { SearchPanel } from "@/components/layout/SearchPanel";
import { apiClient } from "@/lib/api/client";
import { useCorrection } from "@/lib/hooks/useCorrection";
import { useKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";
import { useTheme } from "@/lib/hooks/useTheme";
import { copyToClipboard, downloadCode } from "@/lib/utils/codeActions";
import type { CacheStats, SidebarView } from "@/lib/types/loop";

const initialTrace = {
  input_received: false,
  analysis_completed: false,
  correction_generated: false,
  validation_feedback_received: false,
  self_correction_completed: false,
  final_status: "waiting_for_input" as const,
};

export default function Home() {
  const {
    state,
    activeAttempt,
    loopStatus,
    suggestedTests,
    canSelfCorrect,
    selectSample,
    setCode,
    setLanguage,
    setErrorMessage,
    setUserContext,
    setFeedback,
    setMode,
    setAttempt,
    analyze,
    selfCorrect,
    cancelRequest,
    reset,
    toggleMultiAgent,
    handleFileUpload,
    handleFolderUpload,
    handleMultipleFilesUpload,
    branchFromAttempt,
  } = useCorrection();

  const { theme, toggle: toggleTheme } = useTheme();
  const [activeView, setActiveView] = useState<SidebarView>("explorer");
  const [cacheStats, setCacheStats] = useState<CacheStats | undefined>();

  // Load cache stats when loop panel is shown
  useEffect(() => {
    if (activeView === "loop") {
      apiClient.cacheStats().then(setCacheStats).catch(() => {});
    }
  }, [activeView]);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onAnalyze: analyze,
    onSelfCorrect: canSelfCorrect ? selfCorrect : undefined,
    onCancel: state.loading ? cancelRequest : undefined,
  });

  // Code actions
  const handleCopyCode = useCallback((code: string) => {
    copyToClipboard(code);
  }, []);

  const handleDownloadCode = useCallback((code: string, attemptNumber: number) => {
    downloadCode(code, state.selectedLanguage, attemptNumber);
  }, [state.selectedLanguage]);

  // --- Sidebar panels ---

  const explorer = (
    <ExplorerSidebar
      samples={state.samples}
      selectedLanguage={state.selectedLanguage}
      errorMessage={state.errorMessage}
      userContext={state.userContext}
      loading={state.loading}
      useMultiAgent={state.useMultiAgent}
      onSampleSelect={selectSample}
      onLanguageChange={setLanguage}
      onErrorMessageChange={setErrorMessage}
      onUserContextChange={setUserContext}
      onAnalyze={analyze}
      onReset={reset}
      onFileUpload={handleFileUpload}
      onFolderUpload={handleFolderUpload}
      onMultipleFilesUpload={handleMultipleFilesUpload}
      onToggleMultiAgent={toggleMultiAgent}
    />
  );

  // --- Editor ---

  const editor = (
    <ErrorBoundary fallbackLabel="Editor">
      <section className="editor-shell grid min-h-0 grid-rows-[40px_1fr_230px] bg-[var(--panel)]">
        <EditorTabs mode={state.mode} onModeChange={setMode} />
        <div className="min-h-0">
          {state.mode === "original" && (
            <CodeEditor value={state.originalCode} language={state.selectedLanguage} onChange={setCode} />
          )}
          {state.mode === "fixed" && (
            <CodeEditor value={activeAttempt?.fixed_code ?? ""} language={state.selectedLanguage} readOnly />
          )}
          {state.mode === "diff" && (
            <DiffViewer original={state.originalCode} fixed={activeAttempt?.fixed_code ?? ""} />
          )}
        </div>
        <BottomPanel
          feedback={state.feedback}
          loading={state.loading}
          canSelfCorrect={canSelfCorrect}
          error={state.error}
          suggestedTests={suggestedTests}
          trace={state.session?.loop_trace ?? initialTrace}
          logs={state.logs}
          onFeedbackChange={setFeedback}
          onSelfCorrect={selfCorrect}
        />
      </section>
    </ErrorBoundary>
  );

  // --- Assistant ---

  const assistant = (
    <ErrorBoundary fallbackLabel="Assistant">
      <AssistantPanel
        response={state.session?.assistant_response}
        attempts={state.session?.attempts ?? []}
        selectedAttemptNumber={state.session?.current_attempt_number}
        loading={state.loading}
        error={state.error}
        onAttemptSelect={setAttempt}
        onBranch={branchFromAttempt}
        onCopyCode={handleCopyCode}
        onDownloadCode={handleDownloadCode}
        reviewerVerdict={state.multiAgentResult?.reviewer_verdict}
        testSuite={state.multiAgentResult?.test_suite}
        toolCallsTrace={state.multiAgentResult?.tool_calls_trace}
      />
    </ErrorBoundary>
  );

  return (
    <AppShell
      explorer={explorer}
      searchPanel={<SearchPanel />}
      loopPanel={<LoopPanel cacheStats={cacheStats} sessionId={state.session?.session_id} />}
      problemsPanel={<ProblemsPanel error={state.error} logs={state.logs} />}
      editor={editor}
      assistant={assistant}
      status={loopStatus}
      sessionId={state.session?.session_id}
      attemptCount={state.session?.attempts.length ?? 0}
      activeView={activeView}
      theme={theme}
      onViewChange={setActiveView}
      onThemeToggle={toggleTheme}
    />
  );
}
