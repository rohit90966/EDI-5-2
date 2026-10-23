from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import networkx as nx

from detection.contracts import (
    DetectionFinding,
    DetectorExecutionResult,
    DetectorStatus,
    Severity,
)

GRAPH_DETECTOR_VERSION = "networkx-multigraph-v1.0"


def _parse_ts(val: Any) -> datetime:
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class GraphLaunderingDetector:
    def __init__(
        self,
        max_transactions: int = 1000,
        max_nodes: int = 250,
        max_cycle_length: int = 5,
        max_candidate_paths: int = 50,
        time_budget_sec: float = 3.0,
        fan_threshold: int = 3,
        pass_through_hours: float = 72.0,
    ) -> None:
        self.max_transactions = max_transactions
        self.max_nodes = max_nodes
        self.max_cycle_length = max_cycle_length
        self.max_candidate_paths = max_candidate_paths
        self.time_budget_sec = time_budget_sec
        self.fan_threshold = fan_threshold
        self.pass_through_hours = pass_through_hours

    def build_graph(self, transactions: list[dict[str, Any]]) -> nx.MultiDiGraph:
        """Constructs a directed multigraph from transaction records."""
        G = nx.MultiDiGraph()

        for txn in transactions[: self.max_transactions]:
            txn_id = str(txn.get("txn_id") or "")
            account_id = str(txn.get("account_id") or "ACC_LOCAL")
            counterparty = str(txn.get("counterparty") or f"CP_{txn_id[-4:]}")
            amount = float(txn.get("amount") or 0.0)
            txn_type = str(txn.get("txn_type") or "debit").lower()
            ts = _parse_ts(txn.get("timestamp"))

            # Direction: credit = counterparty -> account; debit = account -> counterparty
            if txn_type == "credit":
                u, v = counterparty, account_id
            else:
                u, v = account_id, counterparty

            edge_key = txn_id if txn_id else f"E_{len(G.edges)}"
            G.add_edge(
                u,
                v,
                key=edge_key,
                source=u,
                target=v,
                txn_id=txn_id or edge_key,
                amount=amount,
                timestamp=ts,
                txn_type=txn_type,
                country=str(txn.get("country") or "").upper(),
            )

        return G

    def analyze(self, transactions: list[dict[str, Any]]) -> DetectorExecutionResult:
        start_time = time.perf_counter()

        if not transactions:
            return DetectorExecutionResult(
                detector_name="graph_detector",
                detector_version=GRAPH_DETECTOR_VERSION,
                status=DetectorStatus.INSUFFICIENT_DATA,
                raw_score=0.0,
                normalized_score=0.0,
                weight=0.40,
                score_contribution=0.0,
                findings=[],
                execution_time_ms=0.0,
                caveats=["No transactions available to construct graph."],
            )

        G = self.build_graph(transactions)
        caveats: list[str] = []
        is_partial = False

        if len(G.nodes) > self.max_nodes:
            caveats.append(f"Node count ({len(G.nodes)}) exceeds safety budget ({self.max_nodes}); graph truncated.")
            is_partial = True

        findings: list[DetectionFinding] = []

        # ── 1. RAPID PASS-THROUGH DETECTION ────────────────────────────
        # Inbound credits followed closely by outbound debits on the same intermediary node
        for node in list(G.nodes):
            if (time.perf_counter() - start_time) > self.time_budget_sec:
                caveats.append("Execution time budget reached during pass-through analysis.")
                is_partial = True
                break

            in_edges = [d for _, _, d in G.in_edges(node, data=True)]
            out_edges = [d for _, _, d in G.out_edges(node, data=True)]

            if not in_edges or not out_edges:
                continue

            for in_e in in_edges:
                in_amt = in_e["amount"]
                in_ts = in_e["timestamp"]

                for out_e in out_edges:
                    out_amt = out_e["amount"]
                    out_ts = out_e["timestamp"]

                    if out_ts >= in_ts:
                        delta_hours = (out_ts - in_ts).total_seconds() / 3600.0
                        if delta_hours <= self.pass_through_hours:
                            # Check amount tolerance: outbound is >= 75% of inbound
                            if in_amt > 0 and (out_amt / in_amt) >= 0.75:
                                finding = DetectionFinding(
                                    finding_id=f"FIND_GRAPH_PT_{uuid4().hex[:8]}",
                                    run_id="",
                                    detector_id="graph_detector",
                                    detector_version=GRAPH_DETECTOR_VERSION,
                                    finding_code="RAPID_PASS_THROUGH",
                                    typology="Pass-Through / Layering",
                                    severity=Severity.HIGH,
                                    score=0.88,
                                    raw_score=round(out_amt / in_amt, 2),
                                    confidence_or_quality=0.90,
                                    reason=(
                                        f"Account {node} received INR {in_amt:,.2f} ({in_e['txn_id']}) "
                                        f"and transferred INR {out_amt:,.2f} ({out_e['txn_id']}) "
                                        f"within {delta_hours:.1f} hours."
                                    ),
                                    reason_code="RAPID_PASS_THROUGH_MOTIF",
                                    evidence_txns=[in_e["txn_id"], out_e["txn_id"]],
                                    evidence_entities=[str(node)],
                                    computed_features={
                                        "inbound_amount": in_amt,
                                        "outbound_amount": out_amt,
                                        "retention_hours": round(delta_hours, 1),
                                    },
                                    graph_path=[str(in_e.get("source", "")), str(node), str(out_e.get("target", ""))],
                                    safe_evidence_summary=(
                                        f"Rapid pass-through: Funds received via {in_e['txn_id']} were "
                                        f"dissipated via {out_e['txn_id']} within {delta_hours:.1f} hours."
                                    ),
                                )
                                findings.append(finding)
                                break  # One finding per node pair to prevent duplication

        # ── 2. BOUNDED CIRCULAR FLOW DETECTION ─────────────────────────
        # Directed cycles in Strongly Connected Components
        sccs = [c for c in nx.strongly_connected_components(G) if len(c) >= 3]
        for scc in sccs:
            if (time.perf_counter() - start_time) > self.time_budget_sec:
                caveats.append("Execution time budget reached during cycle search.")
                is_partial = True
                break

            subG = G.subgraph(scc)
            try:
                # Use simple_cycles with strict length (3 <= len <= max) and candidate count bounds
                cycles_found = 0
                for cycle in nx.simple_cycles(subG):
                    if 3 <= len(cycle) <= self.max_cycle_length:
                        # Extract edge transactions for cycle
                        cycle_txns: list[str] = []
                        for i in range(len(cycle)):
                            u, v = cycle[i], cycle[(i + 1) % len(cycle)]
                            edges = subG.get_edge_data(u, v)
                            if edges:
                                first_edge = next(iter(edges.values()))
                                cycle_txns.append(first_edge["txn_id"])

                        finding = DetectionFinding(
                            finding_id=f"FIND_GRAPH_CYC_{uuid4().hex[:8]}",
                            run_id="",
                            detector_id="graph_detector",
                            detector_version=GRAPH_DETECTOR_VERSION,
                            finding_code="CIRCULAR_FUNDS_FLOW",
                            typology="Round-Trip / Circular Layering",
                            severity=Severity.CRITICAL,
                            score=0.95,
                            raw_score=float(len(cycle)),
                            confidence_or_quality=0.92,
                            reason=(
                                f"Closed circular funds loop detected across {len(cycle)} entities "
                                f"({ ' -> '.join(str(n) for n in cycle) } -> {cycle[0]})."
                            ),
                            reason_code="CIRCULAR_FLOW_MOTIF",
                            evidence_txns=cycle_txns,
                            evidence_entities=[str(n) for n in cycle],
                            graph_path=[str(n) for n in cycle] + [str(cycle[0])],
                            safe_evidence_summary=(
                                f"Circular funds flow detected cycling back to origin through {len(cycle)} entities."
                            ),
                        )
                        findings.append(finding)
                        cycles_found += 1
                        if cycles_found >= 5:
                            break
            except Exception:
                pass

        # ── 3. FAN-IN / FAN-OUT MOTIFS ──────────────────────────────────
        for node in list(G.nodes):
            in_deg = G.in_degree(node)
            out_deg = G.out_degree(node)

            if in_deg >= self.fan_threshold and out_deg >= self.fan_threshold:
                # Collection-distribution mule hub
                in_txns = [d["txn_id"] for _, _, d in G.in_edges(node, data=True)][:4]
                out_txns = [d["txn_id"] for _, _, d in G.out_edges(node, data=True)][:4]

                finding = DetectionFinding(
                    finding_id=f"FIND_GRAPH_HUB_{uuid4().hex[:8]}",
                    run_id="",
                    detector_id="graph_detector",
                    detector_version=GRAPH_DETECTOR_VERSION,
                    finding_code="FAN_IN_FAN_OUT_HUB",
                    typology="Money Mule / Aggregation Hub",
                    severity=Severity.HIGH,
                    score=0.89,
                    raw_score=float(in_deg + out_deg),
                    confidence_or_quality=0.88,
                    reason=(
                        f"Account {node} operates as high-degree hub with {in_deg} distinct inbound sources "
                        f"and {out_deg} outbound dispersals."
                    ),
                    reason_code="HUB_CONVERGENCE_MOTIF",
                    evidence_txns=in_txns + out_txns,
                    evidence_entities=[str(node)],
                    computed_features={"in_degree": in_deg, "out_degree": out_deg},
                    safe_evidence_summary=(
                        f"Aggregation hub pattern: Account {node} exhibits convergent fan-in ({in_deg}) "
                        f"and divergent fan-out ({out_deg})."
                    ),
                )
                findings.append(finding)

        # Compute graph detector normalized score
        if findings:
            max_score = max(f.score for f in findings)
            norm_score = max_score
        else:
            norm_score = 0.0

        weight = 0.40
        score_contrib = round(norm_score * weight, 4)
        elapsed = (time.perf_counter() - start_time) * 1000

        status = DetectorStatus.PARTIAL if is_partial else DetectorStatus.COMPLETE

        return DetectorExecutionResult(
            detector_name="graph_detector",
            detector_version=GRAPH_DETECTOR_VERSION,
            status=status,
            raw_score=round(norm_score, 4),
            normalized_score=round(norm_score, 4),
            weight=weight,
            score_contribution=score_contrib,
            findings=findings,
            execution_time_ms=round(elapsed, 2),
            caveats=caveats if caveats else [f"Evaluated {len(G.nodes)} nodes and {len(G.edges)} edges."],
        )
