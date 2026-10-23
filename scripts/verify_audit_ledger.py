from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from audit.ledger import (
    append_ledger_block,
    reset_in_memory_ledger,
    verify_ledger,
)


def run_tamper_demo() -> bool:
    """
    Deterministic demonstration of the cryptographic hash-chain ledger:
      1. Initializes clean test ledger
      2. Appends 4 valid lifecycle events
      3. Verifies intact ledger
      4. Deliberately mutates a historical block payload
      5. Confirms verifier flags the tampering with exact sequence number and reason
    """
    print("\n" + "=" * 65)
    print("AUDIT LEDGER INTEGRITY & TAMPER-EVIDENT DEMONSTRATION")
    print("=" * 65)

    reset_in_memory_ledger()

    # 1. Create simulated case events
    case_id = "00000000-0000-0000-0000-000000000001"
    print("\n[Step 1] Appending 4 lifecycle events to hash ledger...")

    e1 = append_ledger_block(case_id, "ALERT_INGESTED", {"alert_id": "ALT_101", "amount": 1500000}, actor_id="ingest_svc")
    print(f"  Block 1 appended -> seq: {e1['sequence_number']}, hash: {e1['block_hash'][:16]}...")

    e2 = append_ledger_block(case_id, "DETECTION_RUN_COMPLETED", {"risk_score": 0.88, "tier": "HIGH", "rules": ["AML-001"]}, actor_id="detector_svc")
    print(f"  Block 2 appended -> seq: {e2['sequence_number']}, prev: {e2['prev_hash'][:16]}..., hash: {e2['block_hash'][:16]}...")

    e3 = append_ledger_block(case_id, "SAR_NARRATIVE_GENERATED", {"model": "Qwen2.5-7B", "paragraphs": 5}, actor_id="rag_service")
    print(f"  Block 3 appended -> seq: {e3['sequence_number']}, prev: {e3['prev_hash'][:16]}..., hash: {e3['block_hash'][:16]}...")

    e4 = append_ledger_block(case_id, "ANALYST_APPROVED", {"decision": "APPROVE", "analyst": "analyst_1"}, actor_id="analyst_1")
    print(f"  Block 4 appended -> seq: {e4['sequence_number']}, prev: {e4['prev_hash'][:16]}..., hash: {e4['block_hash'][:16]}...")

    # 2. Verify intact ledger
    print("\n[Step 2] Verifying intact ledger chain...")
    res_clean = verify_ledger()
    print(f"  Result: valid={res_clean.is_valid}, verified_count={res_clean.verified_count}")
    print(f"  Status detail: {res_clean.details}")
    assert res_clean.is_valid is True, "Clean ledger verification failed!"

    # 3. Simulate adversarial tamper on Block 2 payload in test environment
    print("\n[Step 3] Simulating unauthorized edit to Block 2 in database...")
    from audit import ledger
    tampered_chain = copy.deepcopy(ledger._in_memory_ledger)

    # Malicious actor changes risk score from 0.88 to 0.10 to hide suspicion
    print("  -> Malicious edit: Altering Block 2 risk_score from 0.88 to 0.10...")
    tampered_chain[1]["event_payload"]["risk_score"] = 0.10

    # 4. Verify tampered chain
    print("\n[Step 4] Running verifier over tampered ledger...")
    res_tampered = verify_ledger(tampered_chain)
    print(f"  Result: valid={res_tampered.is_valid}")
    print(f"  First failing sequence: {res_tampered.first_failing_sequence}")
    print(f"  Mismatch category: {res_tampered.mismatch_category}")
    print(f"  Detection alert: {res_tampered.details}")

    assert res_tampered.is_valid is False, "Verifier failed to detect payload tampering!"
    assert res_tampered.first_failing_sequence == 2, "Verifier identified wrong block sequence!"
    assert res_tampered.mismatch_category == "PAYLOAD_TAMPER", "Verifier identified wrong mismatch category!"

    print("\n" + "=" * 65)
    print("[SUCCESS] Cryptographic ledger tamper detection verified!")
    print("=" * 65 + "\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Ledger Verification Tool")
    parser.add_argument("--demo", action="store_true", help="Run tamper detection demonstration")
    args = parser.parse_args()

    if args.demo:
        run_tamper_demo()
        return

    res = verify_ledger()
    print(json.dumps(res.model_dump(), indent=2))
    if not res.is_valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
