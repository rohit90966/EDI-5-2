from __future__ import annotations

import random
from typing import Any
from data_generator.models import CustomerProfile

FIRST_NAMES = [
    "Aarav", "Aditi", "Arjun", "Ananya", "Deepak", "Devi", "Gaurav", "Ishaan",
    "Kavita", "Manish", "Meera", "Neha", "Nikhil", "Pooja", "Pranav", "Priya",
    "Rahul", "Rakesh", "Riya", "Rohan", "Sanjay", "Shreya", "Siddharth", "Sneha",
    "Sunil", "Tanvi", "Tarun", "Varun", "Vikram", "Zoya"
]

LAST_NAMES = [
    "Agarwal", "Bose", "Chawla", "Deshmukh", "Gupta", "Iyer", "Jain", "Kapoor",
    "Malhotra", "Mehta", "Menon", "Nair", "Patel", "Rao", "Reddy", "Saxena",
    "Sharma", "Singh", "Soni", "Verma"
]

OCCUPATIONS = [
    {"title": "Salaried employee", "income_range": (35000, 180000), "risk": "LOW"},
    {"title": "Software Engineer", "income_range": (60000, 250000), "risk": "LOW"},
    {"title": "Retail business owner", "income_range": (80000, 450000), "risk": "MEDIUM"},
    {"title": "Student", "income_range": (5000, 25000), "risk": "LOW"},
    {"title": "Retired", "income_range": (25000, 85000), "risk": "LOW"},
    {"title": "Freelance Consultant", "income_range": (45000, 200000), "risk": "LOW"},
    {"title": "Import-Export Trader", "income_range": (150000, 800000), "risk": "MEDIUM"},
    {"title": "Real Estate Broker", "income_range": (70000, 500000), "risk": "MEDIUM"},
]


def create_customer_pool(count: int, rng: random.Random) -> list[CustomerProfile]:
    customers: list[CustomerProfile] = []
    used_names = set()

    for i in range(1, count + 1):
        for _ in range(50):
            fn = rng.choice(FIRST_NAMES)
            ln = rng.choice(LAST_NAMES)
            full_name = f"{fn} {ln}"
            if full_name not in used_names:
                used_names.add(full_name)
                break

        occ_info = rng.choice(OCCUPATIONS)
        inc_min, inc_max = occ_info["income_range"]
        income = round(rng.uniform(inc_min, inc_max), 2)
        
        cid = f"CUST_{i:04d}"
        customers.append(
            CustomerProfile(
                customer_id=cid,
                name=full_name,
                occupation=occ_info["title"],
                monthly_income=income,
                risk_rating=occ_info["risk"],
            )
        )

    return customers
