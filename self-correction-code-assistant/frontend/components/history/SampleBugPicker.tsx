import { FileCode2 } from "lucide-react";

import type { SampleBug } from "@/lib/types/loop";

type SampleBugPickerProps = {
  samples: SampleBug[];
  onSelect: (sample: SampleBug) => void;
};

export function SampleBugPicker({ samples, onSelect }: SampleBugPickerProps) {
  return (
    <section className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Samples</div>
      <div className="space-y-1.5">
        {samples.map((sample) => (
          <button
            key={sample.id}
            onClick={() => onSelect(sample)}
            className="flex w-full items-start gap-2 rounded border border-transparent px-2 py-2 text-left text-sm text-[var(--text)] hover:border-[var(--line)] hover:bg-[var(--panel-3)]"
          >
            <FileCode2 className="mt-0.5 shrink-0 text-[var(--accent)]" size={16} />
            <span>
              <span className="block font-medium">{sample.title}</span>
              <span className="text-xs text-[var(--muted)]">{sample.language}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
