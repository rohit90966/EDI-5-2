from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_generator.config import GeneratorConfig
from data_generator.models import (
    AccountRecord,
    CustomerProfile,
    GroundTruthRecord,
    InvestigationCaseRecord,
    ScenarioRecord,
    TransactionRecord,
)
from data_generator.profiles import create_customer_pool
from data_generator.scenarios import ScenarioGenerator


class SyntheticDataEngine:
    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()
        self.rng = random.Random(self.config.seed)
        self.base_dt = datetime.fromisoformat(self.config.start_date.replace("Z", "+00:00"))
        
        self.customers: list[CustomerProfile] = []
        self.accounts: list[AccountRecord] = []
        self.transactions: list[TransactionRecord] = []
        self.scenarios: list[ScenarioRecord] = []
        self.ground_truth: list[GroundTruthRecord] = []
        self.cases: list[InvestigationCaseRecord] = []

    def generate(self) -> dict[str, Any]:
        """Runs the complete synthetic data generation pipeline."""
        # 1. Generate Customers
        self.customers = create_customer_pool(self.config.num_normal_customers, self.rng)

        # 2. Generate Accounts
        acc_idx = 1
        for cust in self.customers:
            num_accs = 1 if self.rng.random() < 0.75 else 2
            for _ in range(num_accs):
                aid = f"ACC_{acc_idx:05d}"
                acc_idx += 1
                init_bal = round(self.rng.uniform(
                    self.config.default_initial_balance_min,
                    self.config.default_initial_balance_max
                ), 2)
                acc_type = "current" if cust.occupation in ["Retail business owner", "Import-Export Trader"] else "savings"
                self.accounts.append(
                    AccountRecord(
                        account_id=aid,
                        customer_id=cust.customer_id,
                        account_type=acc_type,
                        opened_date=self.base_dt.isoformat(),
                        initial_balance=init_bal,
                        current_balance=init_bal,
                    )
                )

        cust_map = {c.customer_id: c for c in self.customers}
        acc_by_id = {a.account_id: a for a in self.accounts}
        scenario_gen = ScenarioGenerator(self.rng, self.base_dt)

        # 3. Normal Background Activity for every account
        for acc in self.accounts:
            cust = cust_map[acc.customer_id]
            norm_txns, norm_gt = scenario_gen.generate_normal_account_lifecycle(
                acc, cust, days=self.config.simulation_days
            )
            self.transactions.extend(norm_txns)
            self.ground_truth.extend(norm_gt)

        # 4. Inject Hard Negative / Benign Controls
        used_acc_indices = set()
        
        def _get_unused_account() -> AccountRecord:
            for idx in range(len(self.accounts)):
                if idx not in used_acc_indices:
                    used_acc_indices.add(idx)
                    return self.accounts[idx]
            return self.rng.choice(self.accounts)

        # Legitimate bonuses
        for b_idx in range(1, self.config.num_legitimate_bonus_controls + 1):
            acc = _get_unused_account()
            cust = cust_map[acc.customer_id]
            sc, txns, gt = scenario_gen.generate_legitimate_bonus_control(acc, cust, b_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Retail merchant bursts
        for m_idx in range(1, self.config.num_retail_merchant_controls + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_retail_merchant_control(acc, m_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Medical emergency bursts
        for med_idx in range(1, self.config.num_emergency_medical_controls + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_medical_emergency_control(acc, med_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # 5. Inject Suspicious Scenarios (by construction)
        # Structuring
        for s_idx in range(1, self.config.num_structuring_scenarios + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_structuring_scenario(acc, s_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Rapid pass-through
        for p_idx in range(1, self.config.num_passthrough_scenarios + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_rapid_passthrough_scenario(acc, p_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Circular flow (multi-account)
        for c_idx in range(1, self.config.num_circular_scenarios + 1):
            cycle_accs = [_get_unused_account() for _ in range(3)]
            sc, txns, gt = scenario_gen.generate_circular_flow_scenario(cycle_accs, c_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Fan-in Fan-out Hub
        for f_idx in range(1, self.config.num_fan_in_fan_out_scenarios + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_fan_in_fan_out_scenario(acc, f_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # Velocity bursts
        for v_idx in range(1, self.config.num_velocity_burst_scenarios + 1):
            acc = _get_unused_account()
            sc, txns, gt = scenario_gen.generate_velocity_burst_scenario(acc, v_idx)
            self.scenarios.append(sc)
            self.transactions.extend(txns)
            self.ground_truth.extend(gt)

        # 6. Sort Transactions strictly chronologically
        self.transactions.sort(key=lambda t: t.timestamp)
        # Sort ground truth to exactly match chronological transaction order
        txn_order = {t.txn_id: idx for idx, t in enumerate(self.transactions)}
        self.ground_truth.sort(key=lambda g: txn_order.get(g.txn_id, 0))

        # Recompute running balances per account strictly chronologically
        running_balances = {a.account_id: a.initial_balance for a in self.accounts}
        for t in self.transactions:
            curr_b = running_balances.get(t.account_id, 10000.0)
            if t.txn_type == "credit":
                curr_b += t.amount
            else:
                curr_b -= t.amount
            running_balances[t.account_id] = curr_b
            t.balance_after = round(curr_b, 2)

        for a in self.accounts:
            a.current_balance = round(running_balances.get(a.account_id, a.initial_balance), 2)

        # 7. Create Investigation Benchmark Cases
        case_idx = 1
        for sc in self.scenarios:
            cid = f"CASE_SYNTH_{case_idx:04d}"
            case_idx += 1
            primary_acc = sc.involved_accounts[0] if sc.involved_accounts else "ACC_UNKNOWN"
            self.cases.append(
                InvestigationCaseRecord(
                    case_id=cid,
                    scenario_id=sc.scenario_id,
                    account_id=primary_acc,
                    alert_type=sc.scenario_family,
                    alert_timestamp=sc.end_time or sc.start_time,
                    window_start=sc.start_time,
                    window_end=sc.end_time,
                    ground_truth_typology=sc.typology,
                    is_suspicious=sc.is_suspicious_by_construction,
                    transaction_ids=sc.involved_txns,
                )
            )

        summary = {
            "total_customers": len(self.customers),
            "total_accounts": len(self.accounts),
            "total_transactions": len(self.transactions),
            "total_scenarios": len(self.scenarios),
            "total_suspicious_scenarios": sum(1 for s in self.scenarios if s.is_suspicious_by_construction),
            "total_control_scenarios": sum(1 for s in self.scenarios if not s.is_suspicious_by_construction),
            "total_cases": len(self.cases),
            "suspicious_transactions": sum(1 for g in self.ground_truth if g.is_suspicious_by_construction),
            "benign_transactions": sum(1 for g in self.ground_truth if not g.is_suspicious_by_construction),
        }
        return summary

    def export(self, output_dir: str | Path | None = None) -> dict[str, str]:
        """Saves generated datasets to CSV and JSONL files."""
        out_path = Path(output_dir or self.config.output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. transactions.csv
        txns_file = out_path / "transactions.csv"
        with txns_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "txn_id", "account_id", "counterparty", "amount",
                    "txn_type", "country", "timestamp", "balance_after", "purpose_code"
                ],
            )
            writer.writeheader()
            for t in self.transactions:
                writer.writerow(asdict(t))

        # 2. accounts.csv
        accounts_file = out_path / "accounts.csv"
        with accounts_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["account_id", "customer_id", "account_type", "opened_date", "initial_balance", "current_balance"],
            )
            writer.writeheader()
            for a in self.accounts:
                writer.writerow(asdict(a))

        # 3. customers.csv
        cust_file = out_path / "customers.csv"
        with cust_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["customer_id", "name", "occupation", "monthly_income", "risk_rating"],
            )
            writer.writeheader()
            for c in self.customers:
                writer.writerow(asdict(c))

        # 4. scenario_ground_truth.csv
        gt_file = out_path / "scenario_ground_truth.csv"
        with gt_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "txn_id", "account_id", "scenario_id", "scenario_family",
                    "typology", "is_suspicious_by_construction", "is_contextual_only", "confidence"
                ],
            )
            writer.writeheader()
            for g in self.ground_truth:
                writer.writerow(asdict(g))

        # 5. investigation_cases.jsonl
        cases_file = out_path / "investigation_cases.jsonl"
        with cases_file.open("w", encoding="utf-8") as f:
            for c in self.cases:
                f.write(json.dumps(asdict(c)) + "\n")

        # 6. generation_manifest.json
        manifest_file = out_path / "generation_manifest.json"
        manifest_data = {
            "version": "1.0.0",
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "config": asdict(self.config),
            "dataset_statistics": {
                "customers_count": len(self.customers),
                "accounts_count": len(self.accounts),
                "transactions_count": len(self.transactions),
                "scenarios_count": len(self.scenarios),
                "investigation_cases_count": len(self.cases),
                "suspicious_transactions_count": sum(1 for g in self.ground_truth if g.is_suspicious_by_construction),
                "benign_transactions_count": sum(1 for g in self.ground_truth if not g.is_suspicious_by_construction),
            },
            "leakage_safety_declaration": "Zero scenario labels, target flags, or future timestamps are encoded into transactions.csv.",
            "disclaimer": "All accounts, customers, counterparties, and transactions are purely fictional and synthetic for AML benchmark research.",
        }
        with manifest_file.open("w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return {
            "transactions": str(txns_file),
            "accounts": str(accounts_file),
            "customers": str(cust_file),
            "ground_truth": str(gt_file),
            "cases": str(cases_file),
            "manifest": str(manifest_file),
        }
