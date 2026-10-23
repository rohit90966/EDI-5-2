from __future__ import annotations

import hashlib
import math
import time
from typing import Any
from uuid import uuid4

import numpy as np
from sklearn.ensemble import IsolationForest

from detection.contracts import (
    DetectionFinding,
    DetectorExecutionResult,
    DetectorStatus,
    Severity,
)
from .features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_dataset_feature_matrix

MODEL_VERSION = "isoforest-v1.0"
CONTAMINATION_ASSUMPTION = 0.05
RANDOM_SEED = 42


def sigmoid_normalize(raw_score: float) -> float:
    """
    Maps raw scikit-learn IsolationForest decision_function (typically in [-0.5, 0.5])
    to a normalized anomaly score in [0.0, 1.0].
    NOTE: Higher score indicates higher abnormality/outlierness.
    This is an uncalibrated heuristic outlier index, NOT a calibrated probability of crime.
    """
    # Negative decision_function indicates an anomaly in scikit-learn
    # Scale decision_function so negative values yield high scores (>0.60)
    val = -float(raw_score) * 10.0
    return 1.0 / (1.0 + math.exp(-val))


class IsolationForestDetector:
    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = CONTAMINATION_ASSUMPTION,
        random_state: int = RANDOM_SEED,
    ) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model: IsolationForest | None = None
        self.model_hash: str = ""
        self._is_fitted = False

    def fit(self, X: np.ndarray) -> "IsolationForestDetector":
        """Fits the Isolation Forest on a reference/training feature matrix."""
        if len(X) < 5:
            # Cannot robustly fit on fewer than 5 samples
            return self

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.model.fit(X)
        self._is_fitted = True

        # Compute deterministic representation hash
        model_sig = f"IF_{self.n_estimators}_{self.contamination}_{self.random_state}_{len(X)}"
        self.model_hash = hashlib.sha256(model_sig.encode("utf-8")).hexdigest()
        return self

    def save_model(self, file_path: str) -> str:
        """Serializes fitted model with checksum."""
        import pickle
        from pathlib import Path
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as f:
            pickle.dump({"model": self.model, "hash": self.model_hash, "version": MODEL_VERSION}, f)
        return self.model_hash

    def load_model(self, file_path: str) -> "IsolationForestDetector":
        """Loads serialized model artifact."""
        import pickle
        from pathlib import Path
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Model artifact not found: {file_path}")
        with p.open("rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.model_hash = data.get("hash", "")
        self._is_fitted = self.model is not None
        return self

    def analyze_transactions(
        self,
        transactions: list[dict[str, Any]],
        as_of_time: str | None = None,
    ) -> DetectorExecutionResult:
        """
        Executes behavioral anomaly detection on the provided transaction set.
        """
        start_time = time.perf_counter()

        if not transactions:
            return DetectorExecutionResult(
                detector_name="isolation_forest",
                detector_version=MODEL_VERSION,
                status=DetectorStatus.INSUFFICIENT_DATA,
                raw_score=None,
                normalized_score=0.0,
                weight=0.25,
                score_contribution=0.0,
                findings=[],
                execution_time_ms=0.0,
                caveats=["No transactions available to compute behavioral features."],
            )

        if len(transactions) < 5:
            # Sparse account history
            return DetectorExecutionResult(
                detector_name="isolation_forest",
                detector_version=MODEL_VERSION,
                status=DetectorStatus.PARTIAL,
                raw_score=0.0,
                normalized_score=0.1,
                weight=0.25,
                score_contribution=0.025,
                findings=[],
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                caveats=["Account history has fewer than 5 transactions; anomaly scoring has low statistical confidence."],
            )

        # Build features
        X, feat_dicts, txn_ids = build_dataset_feature_matrix(transactions, as_of_time=as_of_time)

        # If model is not pre-fitted, fit on reference window
        if not self._is_fitted:
            self.fit(X)

        if not self._is_fitted or self.model is None:
            return DetectorExecutionResult(
                detector_name="isolation_forest",
                detector_version=MODEL_VERSION,
                status=DetectorStatus.FAILED,
                error_message="Isolation Forest model could not be fitted.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Predict raw decision function and outlier labels (-1 is outlier, 1 is inlier)
        raw_scores = self.model.decision_function(X)
        preds = self.model.predict(X)

        findings: list[DetectionFinding] = []
        normalized_scores: list[float] = []

        for idx, (raw_s, pred, txn_id, f_dict) in enumerate(zip(raw_scores, preds, txn_ids, feat_dicts)):
            norm_s = sigmoid_normalize(raw_s)
            normalized_scores.append(norm_s)

            # Trigger finding if marked outlier by IsolationForest or high normalized score or extreme Z-score
            z_score = abs(float(f_dict.get("amount_mad_zscore", 0.0)))
            is_outlier = (pred == -1) or (norm_s >= 0.65) or (z_score >= 5.0)

            if is_outlier:
                if z_score >= 10.0 or norm_s >= 0.85:
                    severity = Severity.CRITICAL
                elif z_score >= 3.0 or norm_s >= 0.70:
                    severity = Severity.HIGH
                else:
                    severity = Severity.MEDIUM
                
                finding = DetectionFinding(
                    finding_id=f"FIND_IF_{uuid4().hex[:8]}",
                    run_id="",
                    detector_id="isolation_forest",
                    detector_version=MODEL_VERSION,
                    finding_code="BEHAVIORAL_OUTLIER",
                    typology="Unusual Transaction Pattern",
                    severity=severity,
                    score=round(norm_s, 4),
                    raw_score=round(float(raw_s), 4),
                    confidence_or_quality=0.85,
                    reason=(
                        f"Transaction {txn_id} deviates from historical behavioral baseline "
                        f"(Z-score: {f_dict.get('amount_mad_zscore')}, 24h count: {int(f_dict.get('rolling_count_24h', 0))}, "
                        f"velocity: {f_dict.get('velocity_txns_per_day')} txn/day)."
                    ),
                    reason_code="BEHAVIORAL_ANOMALY_DETECTED",
                    evidence_txns=[txn_id],
                    evidence_entities=[],
                    computed_features=f_dict,
                    safe_evidence_summary=(
                        f"Behavioral anomaly identified on transaction {txn_id} with amount "
                        f"INR {f_dict.get('amount', 0):,.2f} exceeding normal profile distribution."
                    ),
                )
                findings.append(finding)

        # Aggregate detector score is max or top-percentile anomaly score
        overall_norm = float(max(normalized_scores)) if normalized_scores else 0.0
        overall_raw = float(min(raw_scores)) if len(raw_scores) > 0 else 0.0

        weight = 0.25
        score_contrib = round(overall_norm * weight, 4)
        elapsed = (time.perf_counter() - start_time) * 1000

        return DetectorExecutionResult(
            detector_name="isolation_forest",
            detector_version=MODEL_VERSION,
            status=DetectorStatus.COMPLETE,
            raw_score=round(overall_raw, 4),
            normalized_score=round(overall_norm, 4),
            weight=weight,
            score_contribution=score_contrib,
            findings=findings,
            execution_time_ms=round(elapsed, 2),
            caveats=[
                "Score reflects unsupervised outlierness and must be evaluated alongside deterministic AML rules.",
                f"Feature schema version: {FEATURE_SCHEMA_VERSION}, model seed: {self.random_state}.",
            ],
        )
