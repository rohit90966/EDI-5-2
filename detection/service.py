from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from audit.ledger import append_ledger_block
from .aggregator import HybridRiskAggregator
from .contracts import (
    AnalysisRunRecord,
    DetectionFinding,
    DetectorExecutionResult,
    DetectorStatus,
)
from .policy import AmlPolicyEngine
from .rules_adapter import RulesEngineDetector
from .snapshot import create_analysis_snapshot
from graph.graph_detector import GraphLaunderingDetector
from ml.anomaly_detector import IsolationForestDetector


class MultiDetectorService:
    def __init__(
        self,
        rules_detector: RulesEngineDetector | None = None,
        anomaly_detector: IsolationForestDetector | None = None,
        graph_detector: GraphLaunderingDetector | None = None,
        aggregator: HybridRiskAggregator | None = None,
        policy_engine: AmlPolicyEngine | None = None,
    ) -> None:
        self.rules_detector = rules_detector or RulesEngineDetector()
        self.anomaly_detector = anomaly_detector or IsolationForestDetector()
        self.graph_detector = graph_detector or GraphLaunderingDetector()
        self.aggregator = aggregator or HybridRiskAggregator()
        self.policy_engine = policy_engine or AmlPolicyEngine()

    def run_analysis(
        self,
        alert_payload: dict[str, Any],
        enrichment: dict[str, Any] | None = None,
        as_of_time: str | None = None,
        case_id: str | None = None,
        idempotency_key: str | None = None,
        db_connection: Any = None,
    ) -> AnalysisRunRecord:
        """
        Executes the three independent detectors, aggregates risk,
        evaluates compliance policy, and records an immutable audit ledger block.
        """
        run_id = f"RUN_{uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        alert_id = str(alert_payload.get("alert_id") or "UNKNOWN_ALERT")
        effective_case_id = case_id or str(uuid4())

        # 1. Create frozen snapshot
        snapshot = create_analysis_snapshot(alert_payload, enrichment=enrichment, as_of_time=as_of_time)

        # 2. Extract transaction list for detectors
        transactions = snapshot.transactions
        if not transactions and enrichment:
            transactions = enrichment.get("transactions") or []

        # 3. Execute Detector A: Deterministic Rules
        # Pass enriched alert if available
        alert_for_rules = dict(alert_payload)
        if enrichment:
            alert_for_rules["enrichment"] = enrichment
            alert_for_rules["raw_transactions"] = transactions
        res_rules = self.rules_detector.analyze(alert_for_rules)

        # 4. Execute Detector B: Behavioral Isolation Forest
        res_anomaly = self.anomaly_detector.analyze_transactions(transactions, as_of_time=snapshot.as_of_time)

        # 5. Execute Detector C: Graph Laundering Patterns
        res_graph = self.graph_detector.analyze(transactions)

        # Collect detector results
        detector_results: dict[str, DetectorExecutionResult] = {
            "rules_engine": res_rules,
            "isolation_forest": res_anomaly,
            "graph_detector": res_graph,
        }

        # Collect all findings and tag with run_id
        all_findings: list[DetectionFinding] = []
        for det_res in detector_results.values():
            for f in det_res.findings:
                f.run_id = run_id
                all_findings.append(f)

        # 6. Aggregate risk scores
        composite_result = self.aggregator.aggregate(detector_results)

        # 7. Evaluate policy decision
        policy_decision = self.policy_engine.evaluate(composite_result, all_findings)

        completed_at = datetime.now(timezone.utc).isoformat()

        # Build run record
        run_record = AnalysisRunRecord(
            run_id=run_id,
            case_id=effective_case_id,
            alert_id=alert_id,
            idempotency_key=idempotency_key,
            status=composite_result.overall_status,
            created_at=created_at,
            completed_at=completed_at,
            as_of_time=snapshot.as_of_time,
            snapshot_hash=snapshot.snapshot_hash,
            rules_version=self.rules_detector.config_version,
            rules_hash=self.rules_detector.config_hash,
            composite_score=composite_result.composite_score,
            risk_tier=composite_result.risk_tier,
            policy_action=policy_decision.action,
            policy_decision=policy_decision,
            detector_results={k: v.model_dump() for k, v in detector_results.items()},
            findings=all_findings,
            warnings=composite_result.data_quality_warnings,
        )

        # 8. Record audit event into append-only hash ledger
        append_ledger_block(
            case_id=effective_case_id,
            action_type="DETECTION_RUN_COMPLETED",
            payload={
                "run_id": run_id,
                "alert_id": alert_id,
                "snapshot_hash": snapshot.snapshot_hash,
                "composite_score": composite_result.composite_score,
                "risk_tier": composite_result.risk_tier,
                "policy_action": policy_decision.action.value,
                "findings_count": len(all_findings),
                "detector_statuses": {k: v.status.value for k, v in detector_results.items()},
            },
            actor_id="system",
            aggregate_type="ANALYSIS_RUN",
            aggregate_id=run_id,
            connection=db_connection,
        )

        return run_record
