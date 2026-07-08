import { ConfidenceBadge, SeverityBadge } from "./Badges";
import { CHANNEL_LABELS, IncidentCase } from "@/lib/types";

function fmtSeconds(v: number | null): string {
  if (v === null) return "—";
  return v < 1 ? `${(v * 1000).toFixed(0)}ms` : `${v.toFixed(1)}s`;
}

export function CaseCard({ c }: { c: IncidentCase }) {
  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold">{CHANNEL_LABELS[c.channel] ?? c.channel}</h3>
          <p className="text-muted text-xs">
            Detected {new Date(c.detected_at).toLocaleString()}
            {c.resolved_at && ` · resolved ${new Date(c.resolved_at).toLocaleTimeString()}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium text-secondary"
          >
            <span
              className="inline-block w-2 h-2 rounded-full shrink-0"
              style={{ background: c.active ? "var(--status-warning)" : "var(--status-good)" }}
              aria-hidden
            />
            {c.active ? "Active" : "Resolved"}
          </span>
          <SeverityBadge severity={c.severity} />
          <ConfidenceBadge confidence={c.confidence} />
        </div>
      </div>

      {c.analysis_error ? (
        <p className="text-sm" style={{ color: "var(--status-critical)" }}>
          Analysis failed: {c.analysis_error}
        </p>
      ) : c.generated_at ? (
        <>
          <p className="text-sm">{c.summary}</p>
          <div>
            <div className="text-muted text-xs mb-1">Likely root cause</div>
            <p className="text-sm text-secondary">{c.likely_root_cause}</p>
          </div>
          {c.recommended_actions.length > 0 && (
            <div>
              <div className="text-muted text-xs mb-1">Recommended actions</div>
              <ul className="text-sm text-secondary list-disc list-inside space-y-0.5">
                {c.recommended_actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="text-xs text-muted pt-1 border-t" style={{ borderColor: "var(--gridline)" }}>
            Time to insight: <span className="text-secondary font-medium">{fmtSeconds(c.time_to_insight_seconds)}</span>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted">Analyzing…</p>
      )}
    </div>
  );
}
