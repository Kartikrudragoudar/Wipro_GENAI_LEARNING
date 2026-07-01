"use client";

import dynamic from "next/dynamic";

import type { Language } from "@/lib/types/loop";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-sm text-[var(--muted)]">Loading editor...</div>,
});

type CodeEditorProps = {
  value: string;
  language: Language;
  readOnly?: boolean;
  onChange?: (value: string) => void;
};

const languageMap: Record<Language, string> = {
  Python: "python",
  JavaScript: "javascript",
  TypeScript: "typescript",
  Java: "java",
  "C++": "cpp",
};

export function CodeEditor({ value, language, readOnly = false, onChange }: CodeEditorProps) {
  return (
    <MonacoEditor
      height="100%"
      language={languageMap[language]}
      value={value}
      theme="vs-dark"
      onChange={(nextValue) => onChange?.(nextValue ?? "")}
      options={{
        readOnly,
        minimap: { enabled: true },
        fontSize: 14,
        fontFamily: "Cascadia Code, Consolas, monospace",
        lineNumbers: "on",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: "on",
      }}
    />
  );
}
