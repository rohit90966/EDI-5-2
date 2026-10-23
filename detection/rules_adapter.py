from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from detection.contracts import (
    DetectionFinding,
    DetectorExecutionResult,
    DetectorStatus,
    Severity,
)
from rag_pipeline.rule_engine import (
    DEFAULT_RULES_PATH,
    calculate_risk_score,
    evaluate_rules,
    load_rule_config,
)

RULES_DETECTOR_VERSION = "rules-yaml-v1"


def compute_rules_hash(rules_path: str | Path = DEFAULT_RULES_PATH) -> tuple[str, str]:
    path = Path(rules_path)
    if not path.exists():
        return "1.0.0", "unknown"
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    version = str(data.get("version", "1"))
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return version, digest


class RulesEngineDetector:
    def __init__(self, rules_path: str | Path = DEFAULT_RULES_PATH) -> None:
        self.rules_path = Path(rules_path)
        self.config_version, self.config_hash = compute_rules_hash(self.rules_path)

    def analyze(self, alert_payload: dict[str, Any]) -> DetectorExecutionResult:
        start_time = time.perf_counter()

        try:
            config = load_rule_config(self.rules_path)
            evidence_blocks = evaluate_rules(alert_payload, config)
            risk_score, risk_level = calculate_risk_score(evidence_blocks)
        except Exception as exc:
            return DetectorExecutionResult(
                detector_name="rules_engine",
                detector_version=RULES_DETECTOR_VERSION,
                status=DetectorStatus.FAILED,
                error_message=f"Rule engine execution error: {exc}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        findings: list[DetectionFinding] = []
        raw_txns = alert_payload.get("raw_transactions") or alert_payload.get("enrichment", {}).get("transactions") or []
        available_txn_ids = [str(t.get("txn_id")) for t in raw_txns if t.get("txn_id")]

        for block in evidence_blocks:
            rule_id = str(block.get("rule_id", "AML-UNKNOWN"))
            confidence = float(block.get("confidence", 0.7))
            obs = str(block.get("observation", ""))
            audit_reason = block.get("audit_reason") or {}
            why_flagged = str(audit_reason.get("why_flagged", obs))
            regulation = str(audit_reason.get("regulation", "FIU-IND Guidelines"))

            severity = (
                Severity.CRITICAL if confidence >= 0.90
                else (Severity.HIGH if confidence >= 0.75
                      else (Severity.MEDIUM if confidence >= 0.50 else Severity.LOW))
            )

            # Match rule-specific transactions if available
            matched_txns: list[str] = []
            if rule_id == "AML-006":
                # Match transactions with destination in high-risk countries
                high_risk = {"UAE", "CAYMAN", "PANAMA", "BAHAMAS", "SEYCHELLES", "MAURITIUS", "VANUATU", "MYANMAR", "IRAN", "NORTH KOREA"}
                matched_txns = [str(t.get("txn_id")) for t in raw_txns if str(t.get("country", "")).upper() in high_risk]
            elif rule_id == "AML-004":
                # Large value transaction >= 1,000,000
                matched_txns = [str(t.get("txn_id")) for t in raw_txns if float(t.get("amount", 0)) >= 1000000]
            elif rule_id in ("AML-001", "AML-002", "AML-003", "AML-007"):
                matched_txns = [str(t.get("txn_id")) for t in raw_txns if t.get("txn_id")]
            
            if not matched_txns and available_txn_ids:
                matched_txns = available_txn_ids[:3]

            finding = DetectionFinding(
                finding_id=f"FIND_RULE_{uuid4().hex[:8]}",
                run_id="",
                detector_id="rules_engine",
                detector_version=RULES_DETECTOR_VERSION,
                finding_code=rule_id,
                typology=block.get("rule_name", "AML Rule Violation"),
                severity=severity,
                score=round(confidence, 4),
                raw_score=round(confidence, 4),
                confidence_or_quality=0.95,
                reason=f"{obs}. Regulation: {regulation}.",
                reason_code=rule_id.replace("-", "_"),
                evidence_txns=matched_txns,
                evidence_entities=[str(alert_payload.get("customer_id") or "")],
                computed_features={"confidence": confidence, "regulation": regulation},
                safe_evidence_summary=f"Rule {rule_id} triggered: {why_flagged}.",
            )
            findings.append(finding)

        weight = 0.35
        score_contrib = round(risk_score * weight, 4)
        elapsed = (time.perf_counter() - start_time) * 1000

        status = DetectorStatus.COMPLETE

        return DetectorExecutionResult(
            detector_name="rules_engine",
            detector_version=RULES_DETECTOR_VERSION,
            status=status,
            raw_score=round(risk_score, 4),
            normalized_score=round(risk_score, 4),
            weight=weight,
            score_contribution=score_contrib,
            findings=findings,
            execution_time_ms=round(elapsed, 2),
            caveats=[f"Rules evaluated from {self.rules_path.name} (hash: {self.config_hash[:10]})."],
        )
