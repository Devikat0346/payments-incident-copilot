"""
Synthetic ground-truth scenarios for evaluating the LLM's diagnostic reasoning.

Each scenario mimics the exact context shape `poller.py` builds from live telemetry,
but with a known, deliberately constructed cause — either a pure latency problem
(elevated p95/p99, success rate near normal) or a pure failure-rate problem (normal
latency, declines/returns concentrated in one or two reason codes). The model is
never told which kind a scenario is; `expected_kind` and `expected_keywords` are
the answer key used only for scoring after the fact.
"""

SCENARIOS = [
    {
        "name": "ecommerce_fraud_spike",
        "expected_kind": "failure",
        "expected_keywords": ["fraud"],
        "context": {
            "channel": "ecommerce",
            "rail": "CARD",
            "normal_baseline": "Typically >96% success (higher decline rate is normal here due to fraud screening), ~250-450ms p50 latency.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 60,
                "success_rate": 0.72,
                "p50_latency_ms": 310,
                "p95_latency_ms": 480,
                "p99_latency_ms": 520,
                "slo_success_rate_target": 0.99,
                "slo_latency_p99_ms_target": 1500,
                "error_budget_burn_pct": 2600,
            },
            "sample_recent_failures": [
                {"status": "declined", "decline_reason": "fraud_suspected", "amount": 240.5, "auth_latency_ms": 300},
                {"status": "declined", "decline_reason": "fraud_suspected", "amount": 180.2, "auth_latency_ms": 295},
                {"status": "declined", "decline_reason": "fraud_suspected", "amount": 90.0, "auth_latency_ms": 310},
                {"status": "declined", "decline_reason": "fraud_suspected", "amount": 410.0, "auth_latency_ms": 305},
            ],
        },
    },
    {
        "name": "wire_branch_latency_spike",
        "expected_kind": "latency",
        "expected_keywords": ["latency", "slow", "delay", "contention", "downstream", "dependen", "timeout", "resourc"],
        "context": {
            "channel": "wire_branch",
            "rail": "WIRE",
            "normal_baseline": "Typically >99.5% success, ~1100-1800ms p50 latency.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 15,
                "success_rate": 0.93,
                "p50_latency_ms": 8200,
                "p95_latency_ms": 11500,
                "p99_latency_ms": 12800,
                "slo_success_rate_target": 0.985,
                "slo_latency_p99_ms_target": 5000,
                "error_budget_burn_pct": 90,
            },
            "sample_recent_failures": [
                {"status": "declined", "decline_reason": "invalid_beneficiary_bank", "amount": 5000.0, "auth_latency_ms": 9100},
            ],
        },
    },
    {
        "name": "zelle_recipient_not_enrolled",
        "expected_kind": "failure",
        "expected_keywords": ["enroll", "recipient"],
        "context": {
            "channel": "zelle_mobile",
            "rail": "ZELLE",
            "normal_baseline": "P2P instant payments via the mobile app. Typically >98% success, ~180-320ms p50 latency (near-instant); failures skew toward recipient-not-enrolled or fraud holds, not technical latency.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 40,
                "success_rate": 0.70,
                "p50_latency_ms": 240,
                "p95_latency_ms": 310,
                "p99_latency_ms": 330,
                "slo_success_rate_target": 0.995,
                "slo_latency_p99_ms_target": 2000,
                "error_budget_burn_pct": 6000,
            },
            "sample_recent_failures": [
                {"status": "declined", "decline_reason": "recipient_not_enrolled", "amount": 50.0, "auth_latency_ms": 250},
                {"status": "declined", "decline_reason": "recipient_not_enrolled", "amount": 120.0, "auth_latency_ms": 245},
                {"status": "declined", "decline_reason": "recipient_not_enrolled", "amount": 75.0, "auth_latency_ms": 260},
            ],
        },
    },
    {
        "name": "loaniq_compliance_hold",
        "expected_kind": "failure",
        "expected_keywords": ["complian", "hold", "regulat"],
        "context": {
            "channel": "wire_loaniq",
            "rail": "WIRE",
            "normal_baseline": "Commercial loan funding wires via LoanIQ. Typically >99% success, ~1700-2700ms p50 latency (slower due to collateral/compliance checks); large dollar amounts.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 10,
                "success_rate": 0.60,
                "p50_latency_ms": 2100,
                "p95_latency_ms": 2600,
                "p99_latency_ms": 2750,
                "slo_success_rate_target": 0.99,
                "slo_latency_p99_ms_target": 5000,
                "error_budget_burn_pct": 4000,
            },
            "sample_recent_failures": [
                {"status": "declined", "decline_reason": "compliance_hold", "amount": 750000.0, "auth_latency_ms": 2200},
                {"status": "declined", "decline_reason": "compliance_hold", "amount": 1200000.0, "auth_latency_ms": 2150},
            ],
        },
    },
    {
        "name": "pos_pure_latency_spike",
        "expected_kind": "latency",
        "expected_keywords": ["latency", "slow", "delay", "contention", "downstream", "dependen", "timeout", "resourc"],
        "context": {
            "channel": "pos",
            "rail": "CARD",
            "normal_baseline": "Typically >99% success, ~150-250ms p50 authorization latency.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 80,
                "success_rate": 0.985,
                "p50_latency_ms": 1400,
                "p95_latency_ms": 1900,
                "p99_latency_ms": 2100,
                "slo_success_rate_target": 0.99,
                "slo_latency_p99_ms_target": 1500,
                "error_budget_burn_pct": 120,
            },
            "sample_recent_failures": [
                {"status": "declined", "decline_reason": "insufficient_funds", "amount": 45.0, "auth_latency_ms": 1350},
            ],
        },
    },
    {
        "name": "ach_batch_nsf_wave",
        "expected_kind": "failure",
        "expected_keywords": ["insufficient", "fund", "nsf"],
        "context": {
            "channel": "ach_batch_file",
            "rail": "ACH_BATCH",
            "normal_baseline": "Typically >98% success per batch run; failures are returns (NSF, closed account) rather than latency.",
            "current_window_metrics": {
                "window_seconds": 300,
                "total_transactions": 50,
                "success_rate": 0.62,
                "p50_latency_ms": None,
                "p95_latency_ms": None,
                "p99_latency_ms": None,
                "slo_success_rate_target": 0.97,
                "slo_latency_p99_ms_target": None,
                "error_budget_burn_pct": 1300,
            },
            "sample_recent_failures": [
                {"status": "returned", "return_code": "R01_insufficient_funds", "amount": 500.0, "auth_latency_ms": None},
                {"status": "returned", "return_code": "R01_insufficient_funds", "amount": 320.0, "auth_latency_ms": None},
                {"status": "returned", "return_code": "R01_insufficient_funds", "amount": 890.0, "auth_latency_ms": None},
                {"status": "returned", "return_code": "R01_insufficient_funds", "amount": 150.0, "auth_latency_ms": None},
            ],
        },
    },
]
