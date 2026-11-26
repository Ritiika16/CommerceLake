import random
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from faker import Faker


fake = Faker("en_US")

# Reproducible data generation
Faker.seed(42)
random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "customers"
    / "batch_001"
)

NUM_CUSTOMERS = 1000


def generate_customers(num_customers: int) -> pd.DataFrame:

    customers = []

    for i in range(1, num_customers + 1):

        created_at = fake.date_time_between(
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
            tzinfo=timezone.utc
        )

        customers.append({
            "customer_id": f"CUST-{i:07d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"customer{i:07d}@example.com",
            "phone": fake.phone_number(),
            "city": fake.city(),
            "state": fake.state(),
            "country": "USA",
            "postal_code": fake.zipcode(),
            "customer_segment": random.choices(
                ["Regular", "Premium", "VIP"],
                weights=[70, 25, 5],
                k=1
            )[0],
            "is_active": random.choices(
                [True, False],
                weights=[95, 5],
                k=1
            )[0],
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat()
        })

    return pd.DataFrame(customers)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_customers(NUM_CUSTOMERS)

    output_file = OUTPUT_DIR / "customers.csv"

    df.to_csv(output_file, index=False)

    print("=" * 60)
    print("CUSTOMER DATA GENERATION COMPLETED")
    print("=" * 60)

    print(f"Total records: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique customers: {df['customer_id'].nunique():,}")
    print(f"Output file: {output_file}")

    print("\nSample records:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()