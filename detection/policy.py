from __future__ import annotations

from .contracts import (
    CompositeScoreResult,
    DetectionFinding,
    DetectorStatus,
    PolicyAction,
    PolicyDecision,
    Severity,
)

POLICY_VERSION = "aml-policy-v1.0"


class AmlPolicyEngine:
    def __init__(
        self,
        sar_draft_threshold: float = 0.50,
        review_threshold: float = 0.25,
        policy_version: str = POLICY_VERSION,
    ) -> None:
        self.sar_draft_threshold = sar_draft_threshold
        self.review_threshold = review_threshold
        self.policy_version = policy_version

    def evaluate(
        self,
        composite_result: CompositeScoreResult,
        findings: list[DetectionFinding],
    ) -> PolicyDecision:
        rationale: list[str] = []
        score = composite_result.composite_score
        status = composite_result.overall_status

        # 1. Check for system incompleteness / failure
        if status == DetectorStatus.FAILED:
            rationale.append("Analysis failed because critical detection subsystems could not execute.")
            return PolicyDecision(
                action=PolicyAction.ANALYSIS_INCOMPLETE,
                is_sar_draft_eligible=False,
                requires_analyst_review=True,
                escalation_level="TECHNICAL_FAILURE",
                policy_version=self.policy_version,
                rationale=rationale,
            )

        if status == DetectorStatus.INSUFFICIENT_DATA:
            rationale.append("Insufficient transaction or KYC history to determine suspicious activity.")
            return PolicyDecision(
                action=PolicyAction.INSUFFICIENT_DATA,
                is_sar_draft_eligible=False,
                requires_analyst_review=False,
                escalation_level="NONE",
                policy_version=self.policy_version,
                rationale=rationale,
            )

        # 2. Check for critical security/laundering findings that trigger immediate SAR eligibility
        has_critical = any(f.severity == Severity.CRITICAL for f in findings)
        rule_findings = [f for f in findings if f.detector_id == "rules_engine"]

        if has_critical or score >= self.sar_draft_threshold or len(rule_findings) >= 2:
            rationale.append(
                f"Composite score ({score:.2f}) meets or exceeds SAR draft threshold ({self.sar_draft_threshold:.2f}) "
                f"or contains critical topological findings."
            )
            for f in findings:
                if f.severity in (Severity.CRITICAL, Severity.HIGH):
                    rationale.append(f"Triggered [{f.finding_code}]: {f.reason}")

            rationale.append("Eligible for SAR narrative drafting. Final filing requires manual compliance officer authorization.")

            return PolicyDecision(
                action=PolicyAction.SAR_DRAFT_ELIGIBLE,
                is_sar_draft_eligible=True,
                requires_analyst_review=True,
                escalation_level="ENHANCED" if (has_critical or score >= 0.75) else "STANDARD",
                policy_version=self.policy_version,
                rationale=rationale,
            )

        # 3. Check for intermediate review threshold or partial detector execution
        if score >= self.review_threshold or len(findings) > 0 or status == DetectorStatus.PARTIAL:
            if status == DetectorStatus.PARTIAL:
                rationale.append(
                    "Detection analysis was PARTIAL (one or more detectors degraded or timed out). "
                    "Analyst review is required to verify unanalyzed risk dimensions."
                )
            else:
                rationale.append(
                    f"Composite risk score ({score:.2f}) exceeds monitoring baseline ({self.review_threshold:.2f}). "
                    "Analyst investigation required to determine if activity is legitimately explainable."
                )
            return PolicyDecision(
                action=PolicyAction.ANALYST_REVIEW_REQUIRED,
                is_sar_draft_eligible=False,
                requires_analyst_review=True,
                escalation_level="STANDARD",
                policy_version=self.policy_version,
                rationale=rationale,
            )

        # 4. Low risk / benign control
        rationale.append(
            f"Composite risk score ({score:.2f}) falls below investigation threshold. "
            "No unusual typology or rule breach observed."
        )
        return PolicyDecision(
            action=PolicyAction.NO_ADDITIONAL_REVIEW_TRIGGERED,
            is_sar_draft_eligible=False,
            requires_analyst_review=False,
            escalation_level="NONE",
            policy_version=self.policy_version,
            rationale=rationale,
        )
