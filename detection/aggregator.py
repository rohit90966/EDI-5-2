from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import (
    CompositeScoreResult,
    DetectorExecutionResult,
    DetectorStatus,
)

DEFAULT_WEIGHTS = {
    "rules_engine": 0.35,
    "isolation_forest": 0.25,
    "graph_detector": 0.40,
}

AGGREGATOR_VERSION = "aggregator-v1.0"


def compute_config_hash(weights: dict[str, float]) -> str:
    raw = json.dumps(weights, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class HybridRiskAggregator:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS
        self._validate_weights()
        self.config_hash = compute_config_hash(self.weights)

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Detector weights must sum to 1.0; got {total:.4f}")

    def aggregate(
        self,
        results: dict[str, DetectorExecutionResult],
    ) -> CompositeScoreResult:
        """
        Combines individual detector results into a unified composite risk score.
        Honors missing or failed detectors without silently treating them as zero.
        """
        data_quality_warnings: list[str] = []
        reason_codes: list[str] = []
        effective_score = 0.0
        active_weight_sum = 0.0

        has_failure = any(r.status == DetectorStatus.FAILED for r in results.values())
        has_insufficient = any(r.status == DetectorStatus.INSUFFICIENT_DATA for r in results.values())
        has_partial = any(r.status == DetectorStatus.PARTIAL for r in results.values())

        for name, weight in self.weights.items():
            res = results.get(name)
            if res is None:
                data_quality_warnings.append(f"Detector '{name}' was not executed.")
                continue

            if res.status == DetectorStatus.FAILED:
                data_quality_warnings.append(
                    f"Detector '{name}' failed during analysis: {res.error_message or 'Unknown error'}."
                )
            elif res.status == DetectorStatus.INSUFFICIENT_DATA:
                data_quality_warnings.append(
                    f"Detector '{name}' had insufficient data to compute an evidence score."
                )
            else:
                effective_score += res.normalized_score * weight
                active_weight_sum += weight

            for finding in res.findings:
                if finding.reason_code not in reason_codes:
                    reason_codes.append(finding.reason_code)

        # If some detectors completed, re-normalize by active weight sum
        if active_weight_sum > 0:
            final_composite = min(max(round(effective_score / active_weight_sum, 4), 0.0), 1.0)
        else:
            final_composite = 0.0

        # Determine overall status
        if has_failure:
            overall_status = DetectorStatus.PARTIAL if active_weight_sum > 0 else DetectorStatus.FAILED
        elif has_insufficient and active_weight_sum == 0:
            overall_status = DetectorStatus.INSUFFICIENT_DATA
        elif has_partial or (active_weight_sum < 0.99):
            overall_status = DetectorStatus.PARTIAL
        else:
            overall_status = DetectorStatus.COMPLETE

        # Risk tier classification
        if final_composite >= 0.75:
            risk_tier = "CRITICAL"
        elif final_composite >= 0.50:
            risk_tier = "HIGH"
        elif final_composite >= 0.25:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        return CompositeScoreResult(
            composite_score=final_composite,
            risk_tier=risk_tier,
            detector_results=results,
            overall_status=overall_status,
            data_quality_warnings=data_quality_warnings,
            reason_codes=reason_codes,
            config_version=AGGREGATOR_VERSION,
            config_hash=self.config_hash,
        )
