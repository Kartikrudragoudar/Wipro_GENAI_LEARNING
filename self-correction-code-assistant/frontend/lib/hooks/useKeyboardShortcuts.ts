"use client";

import { useEffect } from "react";

type ShortcutMap = {
  /** Ctrl+Enter: trigger analyze */
  onAnalyze?: () => void;
  /** Ctrl+Shift+Enter: trigger self-correct */
  onSelfCorrect?: () => void;
  /** Escape: cancel request */
  onCancel?: () => void;
};

export function useKeyboardShortcuts({ onAnalyze, onSelfCorrect, onCancel }: ShortcutMap) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Don't trigger shortcuts when typing in textareas/inputs
      const tag = (e.target as HTMLElement)?.tagName;
      const isTextarea = tag === "TEXTAREA";

      if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && e.shiftKey) {
        e.preventDefault();
        onSelfCorrect?.();
      } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !e.shiftKey && !isTextarea) {
        e.preventDefault();
        onAnalyze?.();
      } else if (e.key === "Escape") {
        onCancel?.();
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onAnalyze, onSelfCorrect, onCancel]);
}
