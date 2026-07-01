"use client";

import dynamic from "next/dynamic";

const ReactDiffViewer = dynamic(() => import("react-diff-viewer-continued"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-sm text-[var(--muted)]">Loading diff...</div>,
});

type DiffViewerProps = {
  original: string;
  fixed: string;
};

export function DiffViewer({ original, fixed }: DiffViewerProps) {
  return (
    <div className="thin-scrollbar h-full overflow-auto bg-[#0b1017] p-3">
      <ReactDiffViewer
        oldValue={original}
        newValue={fixed || "// No correction attempt selected yet."}
        splitView
        useDarkTheme
        leftTitle="Original"
        rightTitle="Fixed attempt"
      />
    </div>
  );
}
