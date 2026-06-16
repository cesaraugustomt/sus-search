import type { SourceCode } from "../types";

interface SourceFilterProps {
  selected: SourceCode | "";
  onChange: (src: SourceCode | "") => void;
}

const SOURCES: { code: SourceCode | ""; label: string; color: string }[] = [
  { code: "", label: "Todas as fontes", color: "#6b7280" },
  { code: "SIGTAP", label: "SIGTAP", color: "#0ea5e9" },
  { code: "CID10", label: "CID-10", color: "#10b981" },
  { code: "CNES", label: "CNES", color: "#8b5cf6" },
];

export function SourceFilter({ selected, onChange }: SourceFilterProps) {
  return (
    <div className="source-filter" role="group" aria-label="Filtrar por fonte">
      {SOURCES.map((s) => (
        <button
          key={s.code}
          type="button"
          className={`source-chip${selected === s.code ? " active" : ""}`}
          style={{ "--chip-color": s.color } as React.CSSProperties}
          onClick={() => onChange(s.code)}
          aria-pressed={selected === s.code}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
