import random
import json
from pathlib import Path
from decimal import Decimal
from datetime import timedelta

import pandas as pd


random.seed(46)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ORDER_FILE = (
    PROJECT_ROOT
    / "data/generated/orders/batch_001/orders.json"
)

ORDER_ITEMS_FILE = (
    PROJECT_ROOT
    / "data/generated/order_items/batch_001/order_items.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/generated/payments/batch_001"
)

PAYMENT_METHODS = [
    "Credit Card",
    "Debit Card",
    "Digital Wallet",
    "Bank Transfer"
]

METHOD_WEIGHTS = [40, 25, 25, 10]


def generate_payments(
    orders: pd.DataFrame,
    order_items: pd.DataFrame
) -> pd.DataFrame:

    payments = []

    # Calculate actual order totals from order items
    order_totals = (
        order_items.groupby("order_id")["net_amount"]
        .sum()
        .to_dict()
    )

    for i, order in enumerate(
        orders.to_dict("records"),
        start=1
    ):

        order_id = order["order_id"]
        order_amount = order_totals[order_id]
        order_status = order["order_status"]

        payment_method = random.choices(
            PAYMENT_METHODS,
            weights=METHOD_WEIGHTS,
            k=1
        )[0]

        paid_amount = Decimal("0.00")
        refund_amount = Decimal("0.00")

        if order_status in ["Delivered", "Shipped"]:

            payment_status = "Completed"
            paid_amount = order_amount

        elif order_status == "Returned":

            payment_status = "Refunded"
            paid_amount = order_amount
            refund_amount = order_amount

        elif order_status == "Cancelled":

            payment_status = "Failed"

        else:

            payment_status = random.choices(
                ["Completed", "Pending"],
                weights=[70, 30],
                k=1
            )[0]

            if payment_status == "Completed":
                paid_amount = order_amount

        net_payment_amount = (
            paid_amount - refund_amount
        )

        order_date = pd.Timestamp(order["order_date"])

        payment_date = order_date + timedelta(
            seconds=random.randint(1, 300)
        )

        refund_date = None
        updated_at = payment_date

        if payment_status == "Refunded":

            refund_date = payment_date + timedelta(
                days=random.randint(3, 15)
            )

            updated_at = refund_date

        payments.append({
            "payment_id": f"PAY-{i:09d}",
            "order_id": order_id,
            "payment_method": payment_method,
            "payment_status": payment_status,
            "order_amount": order_amount,
            "paid_amount": paid_amount,
            "refund_amount": refund_amount,
            "net_payment_amount": net_payment_amount,
            "currency": order["currency"],
            "payment_date": payment_date.isoformat(),
            "refund_date": (
                refund_date.isoformat()
                if refund_date is not None
                else None
            ),
            "created_at": payment_date.isoformat(),
            "updated_at": updated_at.isoformat()
        })

    return pd.DataFrame(payments)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    orders = pd.read_json(
        ORDER_FILE,
        lines=True
    )

    order_items = pd.read_parquet(
        ORDER_ITEMS_FILE
    )

    df = generate_payments(
        orders,
        order_items
    )

    output_file = OUTPUT_DIR / "payments.json"

    # Preserve exact monetary precision in JSON
    with open(output_file, "w", encoding="utf-8") as file:

        for record in df.to_dict("records"):

            file.write(
                json.dumps(record, default=str) + "\n"
            )

    print("=" * 60)
    print("PAYMENT DATA GENERATION COMPLETED")
    print("=" * 60)

    print(f"Total records: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique payments: {df['payment_id'].nunique():,}")
    print(f"Unique orders: {df['order_id'].nunique():,}")

    print(f"Total order amount: ${df['order_amount'].sum():,.2f}")
    print(f"Total paid amount: ${df['paid_amount'].sum():,.2f}")
    print(f"Total refund amount: ${df['refund_amount'].sum():,.2f}")
    print(f"Total net payments: ${df['net_payment_amount'].sum():,.2f}")

    print("\nPayment status distribution:")
    print(df["payment_status"].value_counts())

    print("\nPayment method distribution:")
    print(df["payment_method"].value_counts())

    print(f"\nOutput file: {output_file}")

    print("\nSample records:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()