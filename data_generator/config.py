from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class GeneratorConfig:
    seed: int = 42
    start_date: str = "2026-01-01T00:00:00Z"
    simulation_days: int = 45
    
    # Entity scales
    num_normal_customers: int = 30
    accounts_per_customer_max: int = 2
    
    # Scenario counts
    num_structuring_scenarios: int = 4
    num_passthrough_scenarios: int = 4
    num_circular_scenarios: int = 3
    num_fan_in_fan_out_scenarios: int = 3
    num_velocity_burst_scenarios: int = 3
    num_profile_inconsistency_scenarios: int = 3
    
    # Hard negative controls
    num_legitimate_bonus_controls: int = 4
    num_retail_merchant_controls: int = 4
    num_emergency_medical_controls: int = 3
    num_property_downpayment_controls: int = 3
    
    # Partition ratios
    train_ratio: float = 0.60
    val_ratio: float = 0.20
    test_ratio: float = 0.20
    
    # Balance parameters
    default_initial_balance_min: float = 25000.0
    default_initial_balance_max: float = 150000.0
    
    output_dir: str = "data/synthetic"
