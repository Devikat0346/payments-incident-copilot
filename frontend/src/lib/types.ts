export type Severity = "low" | "medium" | "high";
export type Confidence = "low" | "medium" | "high";

export interface IncidentCase {
  id: string;
  channel: string;
  rail: string;
  detected_at: string;
  resolved_at: string | null;
  generated_at: string | null;
  time_to_insight_seconds: number | null;
  summary: string | null;
  likely_root_cause: string | null;
  confidence: Confidence | null;
  recommended_actions: string[];
  severity: Severity | null;
  analysis_error: string | null;
  metrics_snapshot: Record<string, unknown>;
  sample_failures: Array<{
    status: string;
    decline_reason: string | null;
    return_code: string | null;
    amount: number;
  }>;
  active: boolean;
}

export const CHANNEL_LABELS: Record<string, string> = {
  pos: "POS / Card-Present",
  ecommerce: "E-Commerce",
  mobile_wallet: "Mobile Wallet",
  wire_online: "Wire — Online",
  wire_branch: "Wire — Branch",
  ach_batch_file: "ACH Batch File",
};
