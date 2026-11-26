import random
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd


random.seed(45)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ORDER_FILE = (
    PROJECT_ROOT
    / "data/generated/orders/batch_001/orders.json"
)

PRODUCT_FILE = (
    PROJECT_ROOT
    / "data/generated/products/batch_001/products.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/generated/order_items/batch_001"
)


def round_money(value):
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_order_items(
    orders: pd.DataFrame,
    products: pd.DataFrame
) -> pd.DataFrame:

    order_items = []
    item_id = 1

    product_records = products.to_dict("records")

    for order in orders.to_dict("records"):

        # Each order contains between 1 and 3 products
        num_items = random.choices(
            [1, 2, 3],
            weights=[30, 40, 30],
            k=1
        )[0]

        order_date = pd.Timestamp(order["order_date"])

        # Products must exist before the order date
        eligible_products = [
            product for product in product_records
            if pd.Timestamp(product["created_at"]) <= order_date
        ]

        if not eligible_products:
            raise ValueError(
                f"No eligible products for {order['order_id']}"
            )

        selected_products = random.sample(
            eligible_products,
            k=min(num_items, len(eligible_products))
        )

        for product in selected_products:

            quantity = random.choices(
                [1, 2, 3, 4, 5],
                weights=[60, 25, 10, 4, 1],
                k=1
            )[0]

            unit_price = Decimal(str(product["unit_price"]))
            cost_price = Decimal(str(product["cost_price"]))

            discount_percentage = random.choices(
                [0, 5, 10, 15, 20],
                weights=[50, 20, 15, 10, 5],
                k=1
            )[0]

            gross_amount = round_money(
                unit_price * quantity
            )

            discount_amount = round_money(
                gross_amount
                * Decimal(discount_percentage)
                / Decimal(100)
            )

            net_amount = round_money(
                gross_amount - discount_amount
            )

            total_cost = round_money(
                cost_price * quantity
            )

            profit_amount = round_money(
                net_amount - total_cost
            )

            order_items.append({
                "order_item_id": f"ITEM-{item_id:010d}",
                "order_id": order["order_id"],
                "product_id": product["product_id"],
                "quantity": quantity,
                "unit_price": round_money(unit_price),
                "cost_price": round_money(cost_price),
                "discount_percentage": discount_percentage,
                "gross_amount": gross_amount,
                "discount_amount": discount_amount,
                "net_amount": net_amount,
                "total_cost": total_cost,
                "profit_amount": profit_amount,
                "currency": order["currency"],
                "created_at": order["order_date"],
                "updated_at": order["order_date"]
            })

            item_id += 1

    return pd.DataFrame(order_items)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    orders = pd.read_json(
        ORDER_FILE,
        lines=True
    )

    products = pd.read_csv(PRODUCT_FILE)

    df = generate_order_items(orders, products)

    output_file = OUTPUT_DIR / "order_items.parquet"

    df.to_parquet(
        output_file,
        engine="pyarrow",
        compression="snappy",
        index=False
    )

    print("=" * 60)
    print("ORDER ITEMS DATA GENERATION COMPLETED")
    print("=" * 60)

    print(f"Total records: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique order items: {df['order_item_id'].nunique():,}")
    print(f"Unique orders: {df['order_id'].nunique():,}")
    print(f"Unique products: {df['product_id'].nunique():,}")

    print(f"Total gross amount: ${df['gross_amount'].sum():,.2f}")
    print(f"Total discount: ${df['discount_amount'].sum():,.2f}")
    print(f"Total net amount: ${df['net_amount'].sum():,.2f}")
    print(f"Total profit: ${df['profit_amount'].sum():,.2f}")

    print(f"Output file: {output_file}")

    print("\nSample records:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()