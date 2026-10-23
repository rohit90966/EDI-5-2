from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from data_generator.models import (
    AccountRecord,
    CustomerProfile,
    GroundTruthRecord,
    ScenarioRecord,
    TransactionRecord,
)

MERCHANTS_GROCERY = ["BigBasket", "Blinkit", "DMart Supermarket", "Reliance Fresh", "Nature Basket"]
MERCHANTS_UTILITY = ["BSES Power", "Tata Power", "Airtel Broadband", "Jio Fiber", "Mahanagar Gas"]
MERCHANTS_DINING = ["Zomato", "Swiggy", "Dominos India", "Starbucks Coffee", "Cafe Coffee Day"]
MERCHANTS_HEALTH = ["Apollo Pharmacy", "Fortis Hospital", "Max Healthcare", "1mg Healthcare"]
HIGH_RISK_COUNTRIES = ["UAE", "CAYMAN", "PANAMA", "BAHAMAS", "SEYCHELLES"]


class ScenarioGenerator:
    def __init__(self, rng: random.Random, base_dt: datetime) -> None:
        self.rng = rng
        self.base_dt = base_dt
        self.txn_seq = 1

    def _next_tid(self) -> str:
        tid = f"TXN_{self.txn_seq:06d}"
        self.txn_seq += 1
        return tid

    # ─────────────────────────────────────────────────────────────────────────
    # 1. LEGITIMATE BACKGROUND ACTIVITY
    # ─────────────────────────────────────────────────────────────────────────
    def generate_normal_account_lifecycle(
        self,
        account: AccountRecord,
        customer: CustomerProfile,
        days: int = 90,
    ) -> tuple[list[TransactionRecord], list[GroundTruthRecord]]:
        txns: list[TransactionRecord] = []
        gt: list[GroundTruthRecord] = []

        balance = account.current_balance
        curr_dt = self.base_dt

        # Monthly salary / revenue
        salary_dates = [
            self.base_dt + timedelta(days=d)
            for d in [1, 31, 61]
            if d < days
        ]
        for s_dt in salary_dates:
            amt = round(customer.monthly_income * self.rng.uniform(0.95, 1.05), 2)
            balance += amt
            tid = self._next_tid()
            t = TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=f"CORP_{customer.occupation.replace(' ', '_').upper()}",
                amount=amt,
                txn_type="credit",
                country="IN",
                timestamp=s_dt.isoformat(),
                balance_after=round(balance, 2),
                purpose_code="SALARY",
            )
            txns.append(t)
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id="NORM_BACKGROUND",
                scenario_family="LEGITIMATE",
                typology="BENIGN",
                is_suspicious_by_construction=False,
                is_contextual_only=False,
            ))

        # Regular routine expenditures
        num_spend = self.rng.randint(days // 3, days)
        for _ in range(num_spend):
            spend_dt = self.base_dt + timedelta(
                days=self.rng.randint(0, days - 1),
                hours=self.rng.randint(8, 22),
                minutes=self.rng.randint(0, 59),
            )
            cat = self.rng.choice(["grocery", "utility", "dining", "misc"])
            if cat == "grocery":
                amt = round(self.rng.uniform(400, 4500), 2)
                cp = self.rng.choice(MERCHANTS_GROCERY)
            elif cat == "utility":
                amt = round(self.rng.uniform(800, 3500), 2)
                cp = self.rng.choice(MERCHANTS_UTILITY)
            elif cat == "dining":
                amt = round(self.rng.uniform(250, 1800), 2)
                cp = self.rng.choice(MERCHANTS_DINING)
            else:
                amt = round(self.rng.uniform(100, 2000), 2)
                cp = f"LOCAL_MERCHANT_{self.rng.randint(1, 20)}"

            balance -= amt
            tid = self._next_tid()
            t = TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=cp,
                amount=amt,
                txn_type="debit",
                country="IN",
                timestamp=spend_dt.isoformat(),
                balance_after=round(balance, 2),
                purpose_code="CONSUMPTION",
            )
            txns.append(t)
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id="NORM_BACKGROUND",
                scenario_family="LEGITIMATE",
                typology="BENIGN",
                is_suspicious_by_construction=False,
                is_contextual_only=False,
            ))

        account.current_balance = balance
        return txns, gt

    # ─────────────────────────────────────────────────────────────────────────
    # 2. HARD NEGATIVE / BENIGN CONTROLS
    # ─────────────────────────────────────────────────────────────────────────
    def generate_legitimate_bonus_control(
        self,
        account: AccountRecord,
        customer: CustomerProfile,
        scenario_idx: int,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"CTRL_BONUS_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(20, 50))
        bonus_amt = round(customer.monthly_income * self.rng.uniform(3.0, 5.0), 2)
        
        txns = []
        gt = []

        # 1. Large salary bonus credit
        tid1 = self._next_tid()
        account.current_balance += bonus_amt
        txns.append(TransactionRecord(
            txn_id=tid1,
            account_id=account.account_id,
            counterparty="CORP_ANNUAL_PERFORMANCE_BONUS",
            amount=bonus_amt,
            txn_type="credit",
            country="IN",
            timestamp=t_start.isoformat(),
            balance_after=round(account.current_balance, 2),
            purpose_code="BONUS",
        ))
        gt.append(GroundTruthRecord(
            txn_id=tid1,
            account_id=account.account_id,
            scenario_id=sc_id,
            scenario_family="BENIGN_CONTROL",
            typology="BENIGN_BONUS",
            is_suspicious_by_construction=False,
            is_contextual_only=False,
        ))

        # 2. Investment debit into mutual fund 2 days later
        invest_amt = round(bonus_amt * 0.75, 2)
        tid2 = self._next_tid()
        t_invest = t_start + timedelta(days=2, hours=3)
        account.current_balance -= invest_amt
        txns.append(TransactionRecord(
            txn_id=tid2,
            account_id=account.account_id,
            counterparty="HDFC_MUTUAL_FUND_AMFI",
            amount=invest_amt,
            txn_type="debit",
            country="IN",
            timestamp=t_invest.isoformat(),
            balance_after=round(account.current_balance, 2),
            purpose_code="INVESTMENT",
        ))
        gt.append(GroundTruthRecord(
            txn_id=tid2,
            account_id=account.account_id,
            scenario_id=sc_id,
            scenario_family="BENIGN_CONTROL",
            typology="BENIGN_INVEST",
            is_suspicious_by_construction=False,
            is_contextual_only=False,
        ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="BENIGN_CONTROL",
            typology="BENIGN_BONUS_INVESTMENT",
            is_suspicious_by_construction=False,
            involved_accounts=[account.account_id],
            involved_txns=[tid1, tid2],
            start_time=t_start.isoformat(),
            end_time=t_invest.isoformat(),
            parameters={"bonus_amount": bonus_amt, "invest_amount": invest_amt},
            notes="Legitimate high-value bonus followed by mutual fund deployment. Hard negative for high-amount rules.",
        )
        return scenario, txns, gt

    def generate_retail_merchant_control(
        self,
        account: AccountRecord,
        scenario_idx: int,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"CTRL_MERCHANT_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(15, 60))
        txns = []
        gt = []
        tids = []

        # 15 inward settlements from retail consumers over 12 hours (sale day)
        for i in range(15):
            t_event = t_start + timedelta(minutes=i * 45 + self.rng.randint(2, 20))
            amt = round(self.rng.uniform(600, 4800), 2)
            account.current_balance += amt
            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=f"UPI_RETAIL_BUYER_{self.rng.randint(100, 999)}",
                amount=amt,
                txn_type="credit",
                country="IN",
                timestamp=t_event.isoformat(),
                balance_after=round(account.current_balance, 2),
                purpose_code="POS_SETTLEMENT",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id=sc_id,
                scenario_family="BENIGN_CONTROL",
                typology="BENIGN_MERCHANT",
                is_suspicious_by_construction=False,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="BENIGN_CONTROL",
            typology="BENIGN_RETAIL_FLOW",
            is_suspicious_by_construction=False,
            involved_accounts=[account.account_id],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"burst_count": 15},
            notes="Legitimate merchant high transaction velocity. Hard negative for velocity anomaly detector.",
        )
        return scenario, txns, gt

    def generate_medical_emergency_control(
        self,
        account: AccountRecord,
        scenario_idx: int,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"CTRL_MEDICAL_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(20, 65))
        txns = []
        gt = []
        tids = []

        # Rapid withdrawal / payment for medical emergency
        for i in range(3):
            t_event = t_start + timedelta(hours=i * 4)
            amt = round(self.rng.uniform(45000, 95000), 2)
            account.current_balance -= amt
            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=self.rng.choice(MERCHANTS_HEALTH),
                amount=amt,
                txn_type="debit",
                country="IN",
                timestamp=t_event.isoformat(),
                balance_after=round(account.current_balance, 2),
                purpose_code="HOSPITAL_EXPENSES",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id=sc_id,
                scenario_family="BENIGN_CONTROL",
                typology="BENIGN_EMERGENCY",
                is_suspicious_by_construction=False,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="BENIGN_CONTROL",
            typology="BENIGN_MEDICAL_EMERGENCY",
            is_suspicious_by_construction=False,
            involved_accounts=[account.account_id],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"medical_withdrawals": 3},
            notes="Legitimate hospital payments with rapid consecutive debits. Hard negative for velocity & amount anomalies.",
        )
        return scenario, txns, gt

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SUSPICIOUS SCENARIOS (BY CONSTRUCTION)
    # ─────────────────────────────────────────────────────────────────────────
    def generate_structuring_scenario(
        self,
        account: AccountRecord,
        scenario_idx: int,
        count: int = 22,
        threshold: float = 50000.0,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"SUSP_STRUCT_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(10, 70))
        txns = []
        gt = []
        tids = []

        # Repeated cash/wire deposits just below threshold
        curr_dt = t_start
        for i in range(count):
            curr_dt += timedelta(hours=self.rng.randint(1, 4), minutes=self.rng.randint(5, 45))
            amt = round(self.rng.uniform(threshold * 0.94, threshold * 0.99), 2)
            account.current_balance += amt
            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=f"CASH_DEPOSIT_BRANCH_{self.rng.randint(1, 5)}",
                amount=amt,
                txn_type="credit",
                country="IN",
                timestamp=curr_dt.isoformat(),
                balance_after=round(account.current_balance, 2),
                purpose_code="CASH_DEPOSIT",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id=sc_id,
                scenario_family="STRUCTURING",
                typology="STRUCTURING",
                is_suspicious_by_construction=True,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="STRUCTURING",
            typology="STRUCTURING_SMURFING",
            is_suspicious_by_construction=True,
            involved_accounts=[account.account_id],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"deposit_count": count, "threshold": threshold},
            notes="Smurfing structuring sequence: repeated deposits just below reporting limit.",
        )
        return scenario, txns, gt

    def generate_rapid_passthrough_scenario(
        self,
        account: AccountRecord,
        scenario_idx: int,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"SUSP_PASSTHRU_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(10, 75))
        txns = []
        gt = []
        tids = []

        # Inward bulk credit from unverified source
        in_amt = round(self.rng.uniform(1200000, 2500000), 2)
        account.current_balance += in_amt
        tid_in = self._next_tid()
        tids.append(tid_in)
        txns.append(TransactionRecord(
            txn_id=tid_in,
            account_id=account.account_id,
            counterparty=f"OPAQUE_HOLDINGS_SOURCE_{self.rng.randint(1, 10)}",
            amount=in_amt,
            txn_type="credit",
            country="IN",
            timestamp=t_start.isoformat(),
            balance_after=round(account.current_balance, 2),
            purpose_code="CONSULTANCY",
        ))
        gt.append(GroundTruthRecord(
            txn_id=tid_in,
            account_id=account.account_id,
            scenario_id=sc_id,
            scenario_family="PASS_THROUGH",
            typology="PASS_THROUGH",
            is_suspicious_by_construction=True,
            is_contextual_only=False,
        ))

        # Rapid outward dissipation within 6-12 hours to high-risk jurisdiction (UAE)
        t_out = t_start + timedelta(hours=self.rng.randint(4, 10))
        out_amt = round(in_amt * self.rng.uniform(0.97, 0.99), 2)
        account.current_balance -= out_amt
        tid_out = self._next_tid()
        tids.append(tid_out)
        txns.append(TransactionRecord(
            txn_id=tid_out,
            account_id=account.account_id,
            counterparty=f"SHELL_LOGISTICS_{self.rng.choice(HIGH_RISK_COUNTRIES)}",
            amount=out_amt,
            txn_type="debit",
            country=self.rng.choice(HIGH_RISK_COUNTRIES),
            timestamp=t_out.isoformat(),
            balance_after=round(account.current_balance, 2),
            purpose_code="OFFSHORE_REMITTANCE",
        ))
        gt.append(GroundTruthRecord(
            txn_id=tid_out,
            account_id=account.account_id,
            scenario_id=sc_id,
            scenario_family="PASS_THROUGH",
            typology="PASS_THROUGH",
            is_suspicious_by_construction=True,
            is_contextual_only=False,
        ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="PASS_THROUGH",
            typology="RAPID_PASS_THROUGH",
            is_suspicious_by_construction=True,
            involved_accounts=[account.account_id],
            involved_txns=tids,
            start_time=t_start.isoformat(),
            end_time=t_out.isoformat(),
            parameters={"in_amount": in_amt, "out_amount": out_amt, "delta_hours": (t_out - t_start).total_seconds() / 3600},
            notes="Rapid layering: high-value inward credit drained to offshore shell company.",
        )
        return scenario, txns, gt

    def generate_circular_flow_scenario(
        self,
        accounts: list[AccountRecord],
        scenario_idx: int,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        assert len(accounts) >= 3, "Circular flow requires at least 3 accounts"
        sc_id = f"SUSP_CIRCULAR_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(15, 70))
        txns = []
        gt = []
        tids = []

        base_amt = round(self.rng.uniform(700000, 1500000), 2)
        curr_dt = t_start
        cycle_len = len(accounts)

        for i in range(cycle_len):
            src_acc = accounts[i]
            dst_acc = accounts[(i + 1) % cycle_len]
            # Deduct fee / haircut
            step_amt = round(base_amt - (i * self.rng.uniform(3000, 8000)), 2)
            
            curr_dt += timedelta(hours=self.rng.randint(6, 14))
            src_acc.current_balance -= step_amt
            dst_acc.current_balance += step_amt

            # Source debit
            tid_deb = self._next_tid()
            tids.append(tid_deb)
            txns.append(TransactionRecord(
                txn_id=tid_deb,
                account_id=src_acc.account_id,
                counterparty=dst_acc.account_id,
                amount=step_amt,
                txn_type="debit",
                country="IN",
                timestamp=curr_dt.isoformat(),
                balance_after=round(src_acc.current_balance, 2),
                purpose_code="INTER_COMPANY_TRANSFER",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid_deb,
                account_id=src_acc.account_id,
                scenario_id=sc_id,
                scenario_family="CIRCULAR_FLOW",
                typology="CIRCULAR_FLOW",
                is_suspicious_by_construction=True,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="CIRCULAR_FLOW",
            typology="ROUND_TRIPPING_CYCLE",
            is_suspicious_by_construction=True,
            involved_accounts=[a.account_id for a in accounts],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"cycle_length": cycle_len, "base_amount": base_amt},
            notes="Round-tripping loop through multiple layered intermediary entities.",
        )
        return scenario, txns, gt

    def generate_fan_in_fan_out_scenario(
        self,
        hub_account: AccountRecord,
        scenario_idx: int,
        fan_count: int = 5,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"SUSP_FAN_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(20, 75))
        txns = []
        gt = []
        tids = []

        total_collected = 0.0
        # Phase 1: Fan-in (Multiple sources credit the hub)
        for i in range(fan_count):
            t_in = t_start + timedelta(hours=i * 2 + self.rng.randint(0, 1))
            amt = round(self.rng.uniform(60000, 140000), 2)
            total_collected += amt
            hub_account.current_balance += amt
            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=hub_account.account_id,
                counterparty=f"VICTIM_P2P_FEEDER_{i+1}",
                amount=amt,
                txn_type="credit",
                country="IN",
                timestamp=t_in.isoformat(),
                balance_after=round(hub_account.current_balance, 2),
                purpose_code="SETTLEMENT",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=hub_account.account_id,
                scenario_id=sc_id,
                scenario_family="FAN_IN_FAN_OUT",
                typology="FAN_IN_FAN_OUT",
                is_suspicious_by_construction=True,
                is_contextual_only=False,
            ))

        # Phase 2: Fan-out (Hub disperses funds to downstream money mules)
        t_phase2 = t_start + timedelta(hours=fan_count * 2 + 4)
        split_amt = round((total_collected * 0.96) / fan_count, 2)
        for j in range(fan_count):
            t_out = t_phase2 + timedelta(hours=j * 2)
            hub_account.current_balance -= split_amt
            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=hub_account.account_id,
                counterparty=f"MULE_WITHDRAWAL_ACC_{j+1}",
                amount=split_amt,
                txn_type="debit",
                country="IN",
                timestamp=t_out.isoformat(),
                balance_after=round(hub_account.current_balance, 2),
                purpose_code="DISBURSEMENT",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=hub_account.account_id,
                scenario_id=sc_id,
                scenario_family="FAN_IN_FAN_OUT",
                typology="FAN_IN_FAN_OUT",
                is_suspicious_by_construction=True,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="FAN_IN_FAN_OUT",
            typology="MULE_COLLECTION_HUB",
            is_suspicious_by_construction=True,
            involved_accounts=[hub_account.account_id],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"fan_count": fan_count, "total_collected": total_collected},
            notes="Mule collection aggregation hub with fan-in followed immediately by fan-out dissipation.",
        )
        return scenario, txns, gt

    def generate_velocity_burst_scenario(
        self,
        account: AccountRecord,
        scenario_idx: int,
        burst_count: int = 18,
    ) -> tuple[ScenarioRecord, list[TransactionRecord], list[GroundTruthRecord]]:
        sc_id = f"SUSP_VELOCITY_{scenario_idx:02d}"
        t_start = self.base_dt + timedelta(days=self.rng.randint(15, 75))
        txns = []
        gt = []
        tids = []

        curr_dt = t_start
        for i in range(burst_count):
            curr_dt += timedelta(minutes=self.rng.randint(8, 25))
            amt = round(self.rng.uniform(35000, 95000), 2)
            ttype = "debit" if self.rng.random() < 0.7 else "credit"
            if ttype == "debit":
                account.current_balance -= amt
            else:
                account.current_balance += amt

            tid = self._next_tid()
            tids.append(tid)
            txns.append(TransactionRecord(
                txn_id=tid,
                account_id=account.account_id,
                counterparty=f"BURST_TARGET_{i % 4}",
                amount=amt,
                txn_type=ttype,
                country="IN",
                timestamp=curr_dt.isoformat(),
                balance_after=round(account.current_balance, 2),
                purpose_code="ONLINE_TRANSFER",
            ))
            gt.append(GroundTruthRecord(
                txn_id=tid,
                account_id=account.account_id,
                scenario_id=sc_id,
                scenario_family="VELOCITY_ANOMALY",
                typology="TRANSACTION_BURST",
                is_suspicious_by_construction=True,
                is_contextual_only=False,
            ))

        scenario = ScenarioRecord(
            scenario_id=sc_id,
            scenario_family="VELOCITY_ANOMALY",
            typology="TRANSACTION_VELOCITY_BURST",
            is_suspicious_by_construction=True,
            involved_accounts=[account.account_id],
            involved_txns=tids,
            start_time=txns[0].timestamp,
            end_time=txns[-1].timestamp,
            parameters={"burst_count": burst_count},
            notes="Abnormal transaction frequency burst drastically exceeding account historical baseline.",
        )
        return scenario, txns, gt
