import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd


random.seed(44)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CUSTOMER_FILE = (
    PROJECT_ROOT
    / "data/generated/customers/batch_001/customers.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/generated/orders/batch_001"
)

NUM_ORDERS = 5000

ORDER_STATUSES = [
    "Delivered",
    "Shipped",
    "Processing",
    "Cancelled",
    "Returned"
]

STATUS_WEIGHTS = [70, 10, 8, 7, 5]

SALES_CHANNELS = [
    "Website",
    "Mobile App",
    "Marketplace"
]

CHANNEL_WEIGHTS = [45, 40, 15]


def generate_orders(
    num_orders: int,
    customers: pd.DataFrame
) -> pd.DataFrame:

    orders = []

    customer_records = customers.to_dict("records")

    end_date = datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )

    for i in range(1, num_orders + 1):

        customer = random.choice(customer_records)

        customer_created_at = datetime.fromisoformat(
            customer["created_at"]
        )

        # Orders cannot exist before customer registration
        available_seconds = int(
            (end_date - customer_created_at).total_seconds()
        )

        order_date = customer_created_at + timedelta(
            seconds=random.randint(0, available_seconds)
        )

        order_status = random.choices(
            ORDER_STATUSES,
            weights=STATUS_WEIGHTS,
            k=1
        )[0]

        sales_channel = random.choices(
            SALES_CHANNELS,
            weights=CHANNEL_WEIGHTS,
            k=1
        )[0]

        orders.append({
            "order_id": f"ORD-{i:09d}",
            "customer_id": customer["customer_id"],
            "order_date": order_date.isoformat(),
            "order_status": order_status,
            "sales_channel": sales_channel,
            "currency": "USD",
            "shipping_city": customer["city"],
            "shipping_state": customer["state"],
            "shipping_country": customer["country"],
            "created_at": order_date.isoformat(),
            "updated_at": order_date.isoformat()
        })

    return pd.DataFrame(orders)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    customers = pd.read_csv(
        CUSTOMER_FILE,
        dtype={"postal_code": str}
    )

    df = generate_orders(NUM_ORDERS, customers)

    output_file = OUTPUT_DIR / "orders.json"

    df.to_json(
        output_file,
        orient="records",
        lines=True,
        force_ascii=False
    )

    print("=" * 60)
    print("ORDER DATA GENERATION COMPLETED")
    print("=" * 60)

    print(f"Total records: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique orders: {df['order_id'].nunique():,}")
    print(f"Unique customers: {df['customer_id'].nunique():,}")
    print(f"Output file: {output_file}")

    print("\nSample records:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()