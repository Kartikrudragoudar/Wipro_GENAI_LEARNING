import type { Language } from "@/lib/types/loop";

const extensionMap: Record<Language, string> = {
  Python: "py",
  JavaScript: "js",
  TypeScript: "ts",
  Java: "java",
  "C++": "cpp",
};

export function downloadCode(code: string, language: Language, attemptNumber: number) {
  const ext = extensionMap[language] ?? "txt";
  const filename = `fixed_attempt_${attemptNumber}.${ext}`;
  const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}
