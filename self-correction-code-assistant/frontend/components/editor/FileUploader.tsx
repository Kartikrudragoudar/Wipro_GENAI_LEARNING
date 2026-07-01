"use client";

import { FileUp, FolderUp, Upload } from "lucide-react";
import { useRef, useState } from "react";

type FileUploaderProps = {
  loading: boolean;
  onFileUpload: (file: File) => void;
  onFolderUpload: (file: File) => void;
  onMultipleFilesUpload: (files: File[]) => void;
};

export function FileUploader({ loading, onFileUpload, onFolderUpload, onMultipleFilesUpload }: FileUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const multiInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFileUpload(file);
    event.target.value = "";
  }

  function handleFolderChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFolderUpload(file);
    event.target.value = "";
  }

  function handleMultiChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (files && files.length > 0) {
      onMultipleFilesUpload(Array.from(files));
    }
    event.target.value = "";
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!loading) setDragActive(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (loading) return;

    const files = Array.from(event.dataTransfer.files);
    if (files.length === 0) return;

    if (files.length === 1) {
      const [file] = files;
      if (file.name.toLowerCase().endsWith(".zip")) {
        onFolderUpload(file);
      } else {
        onFileUpload(file);
      }
      return;
    }

    onMultipleFilesUpload(files);
  }

  return (
    <section className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Upload Code</div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded border border-dashed px-3 py-4 text-center text-sm transition ${
          dragActive
            ? "border-[var(--accent)] bg-[var(--panel-3)] text-white"
            : "border-[var(--line)] bg-[var(--panel-2)] text-[var(--muted)]"
        } ${loading ? "opacity-50" : "hover:border-[var(--accent)] hover:text-white"}`}
      >
        <Upload size={18} className="mx-auto mb-2 text-[var(--accent)]" />
        <div className="font-medium">Drop files here</div>
        <div className="mt-1 text-xs">Single file, multiple files, or a .zip folder</div>
      </div>
      <div className="grid grid-cols-1 gap-2">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="flex w-full items-center gap-2 rounded border border-[var(--line)] px-2 py-2 text-left text-sm text-[var(--text)] hover:bg-[var(--panel-3)] disabled:opacity-50"
        >
          <FileUp size={15} className="shrink-0 text-[var(--accent)]" />
          <span>Upload file</span>
        </button>

        <button
          onClick={() => multiInputRef.current?.click()}
          disabled={loading}
          className="flex w-full items-center gap-2 rounded border border-[var(--line)] px-2 py-2 text-left text-sm text-[var(--text)] hover:bg-[var(--panel-3)] disabled:opacity-50"
        >
          <Upload size={15} className="shrink-0 text-[var(--accent)]" />
          <span>Upload multiple files</span>
        </button>

        <button
          onClick={() => folderInputRef.current?.click()}
          disabled={loading}
          className="flex w-full items-center gap-2 rounded border border-[var(--line)] px-2 py-2 text-left text-sm text-[var(--text)] hover:bg-[var(--panel-3)] disabled:opacity-50"
        >
          <FolderUp size={15} className="shrink-0 text-[var(--accent)]" />
          <span>Upload folder (.zip)</span>
        </button>
      </div>

      {/* Hidden file inputs */}
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} accept=".py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.sh,.sql,.html,.css,.scss,.json,.yaml,.yml,.toml,.xml,.md,.txt" />
      <input ref={folderInputRef} type="file" className="hidden" onChange={handleFolderChange} accept=".zip" />
      <input ref={multiInputRef} type="file" className="hidden" onChange={handleMultiChange} multiple accept=".py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.sh,.sql,.html,.css,.scss,.json,.yaml,.yml,.toml,.xml,.md,.txt" />
    </section>
  );
}
