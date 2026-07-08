import { Confidence, Severity } from "@/lib/types";

const SEVERITY_COLOR: Record<Severity, string> = {
  low: "var(--status-good)",
  medium: "var(--status-warning)",
  high: "var(--status-critical)",
};

export function SeverityBadge({ severity }: { severity: Severity | null }) {
  if (!severity) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-secondary">
      <span
        className="inline-block w-2 h-2 rounded-full shrink-0"
        style={{ background: SEVERITY_COLOR[severity] }}
        aria-hidden
      />
      {severity[0].toUpperCase() + severity.slice(1)} severity
    </span>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence | null }) {
  if (!confidence) return null;
  return (
    <span className="text-xs text-muted border rounded-full px-2 py-0.5" style={{ borderColor: "var(--border)" }}>
      {confidence} confidence
    </span>
  );
}
