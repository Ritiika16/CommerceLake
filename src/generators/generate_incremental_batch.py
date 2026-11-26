import json
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
from faker import Faker


# ==================================================
# 1. PROJECT CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "generated"

PREVIOUS_BATCH = "batch_001"
CURRENT_BATCH = "batch_002"

RANDOM_SEED = 47

random.seed(RANDOM_SEED)

fake = Faker("en_US")
Faker.seed(RANDOM_SEED)


# ==================================================
# 2. INCREMENTAL BATCH CONFIGURATION
# ==================================================

NUM_NEW_CUSTOMERS = 200
NUM_NEW_PRODUCTS = 50
NUM_NEW_ORDERS = 1000

BATCH_START_DATE = datetime(
    2026, 1, 1, tzinfo=timezone.utc
)

BATCH_END_DATE = datetime(
    2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc
)

SOURCE_CONFIG = {
    "customers": {
        "filename": "customers.csv",
        "primary_key": "customer_id"
    },
    "products": {
        "filename": "products.csv",
        "primary_key": "product_id"
    },
    "orders": {
        "filename": "orders.json",
        "primary_key": "order_id"
    },
    "order_items": {
        "filename": "order_items.parquet",
        "primary_key": "order_item_id"
    },
    "payments": {
        "filename": "payments.json",
        "primary_key": "payment_id"
    }
}


# ==================================================
# 3. HISTORICAL DATA LOADER
# ==================================================

def load_historical_data() -> dict:

    historical_data = {}

    for entity, config in SOURCE_CONFIG.items():

        file_path = (
            DATA_DIR
            / entity
            / PREVIOUS_BATCH
            / config["filename"]
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Historical source file not found: {file_path}"
            )

        if file_path.suffix == ".csv":

            df = pd.read_csv(
                file_path,
                dtype={"postal_code": str}
                if entity == "customers"
                else None
            )

        elif file_path.suffix == ".json":

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                records = [
                    json.loads(line)
                    for line in file
                    if line.strip()
                ]

            df = pd.DataFrame(records)

        elif file_path.suffix == ".parquet":

            df = pd.read_parquet(file_path)

        else:

            raise ValueError(
                f"Unsupported file format: {file_path.suffix}"
            )

        historical_data[entity] = df

    return historical_data


# ==================================================
# 4. DYNAMIC ID MANAGEMENT
# ==================================================

def get_next_id(
    df: pd.DataFrame,
    primary_key: str
) -> int:

    numeric_ids = (
        df[primary_key]
        .astype(str)
        .str.split("-")
        .str[-1]
        .astype(int)
    )

    return int(numeric_ids.max()) + 1

# ==================================================
# 5. INCREMENTAL CUSTOMER GENERATOR
# ==================================================

def generate_incremental_customers(
    historical_customers: pd.DataFrame
) -> pd.DataFrame:

    customers = []

    start_id = get_next_id(
        historical_customers,
        "customer_id"
    )

    for i in range(
        start_id,
        start_id + NUM_NEW_CUSTOMERS
    ):

        created_at = fake.date_time_between(
            start_date=BATCH_START_DATE,
            end_date=BATCH_END_DATE,
            tzinfo=timezone.utc
        )

        customer = {
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
        }

        customers.append(customer)

    df = pd.DataFrame(customers)

    return df

# ==================================================
# 6. INCREMENTAL PRODUCT GENERATOR
# ==================================================

def generate_incremental_products(
    historical_products: pd.DataFrame
) -> pd.DataFrame:

    products = []

    start_id = get_next_id(
        historical_products,
        "product_id"
    )

    category_price_ranges = {
        "Electronics": (20, 2000),
        "Fashion": (10, 250),
        "Home & Kitchen": (15, 500),
        "Beauty": (5, 150),
        "Sports": (10, 400)
    }

    brands = [
        "Nova",
        "Vertex",
        "Apex",
        "UrbanEdge",
        "Prime",
        "Zenith",
        "Elite",
        "Everest"
    ]

    for i in range(
        start_id,
        start_id + NUM_NEW_PRODUCTS
    ):

        category = random.choice(
            list(category_price_ranges.keys())
        )

        min_price, max_price = category_price_ranges[category]

        unit_price = round(
            random.uniform(min_price, max_price),
            2
        )

        cost_price = round(
            unit_price * random.uniform(0.4, 0.8),
            2
        )

        brand = random.choice(brands)

        created_at = fake.date_time_between(
            start_date=BATCH_START_DATE,
            end_date=BATCH_END_DATE,
            tzinfo=timezone.utc
        )

        product = {
            "product_id": f"PROD-{i:07d}",
            "sku": f"SKU-{i:07d}",
            "product_name": f"{brand} {category} Product {i}",
            "category": category,
            "brand": brand,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "currency": "USD",
            "stock_quantity": random.randint(0, 1000),

            "is_active": random.choices(
                [True, False],
                weights=[95, 5],
                k=1
            )[0],

            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat()
        }

        products.append(product)

    return pd.DataFrame(products)

# ==================================================
# 7. INCREMENTAL ORDER GENERATOR
# ==================================================

def generate_incremental_orders(
    historical_orders: pd.DataFrame,
    historical_customers: pd.DataFrame,
    new_customers: pd.DataFrame
) -> pd.DataFrame:

    orders = []

    start_id = get_next_id(
        historical_orders,
        "order_id"
    )

    # Combine historical and incremental customers
    all_customers = pd.concat(
        [historical_customers, new_customers],
        ignore_index=True
    )

    all_customers["created_at"] = pd.to_datetime(
        all_customers["created_at"],
        utc=True,
        format="mixed"
    )

    for i in range(
        start_id,
        start_id + NUM_NEW_ORDERS
    ):

        order_date = fake.date_time_between(
            start_date=BATCH_START_DATE,
            end_date=BATCH_END_DATE,
            tzinfo=timezone.utc
        )

        # Only customers registered before the order
        eligible_customers = all_customers[
            all_customers["created_at"] <= order_date
        ]

        if eligible_customers.empty:
            raise ValueError(
                f"No eligible customers for {order_date}"
            )

        customer = eligible_customers.iloc[
            random.randrange(len(eligible_customers))
        ]

        order_status = random.choices(
            [
                "Delivered",
                "Shipped",
                "Processing",
                "Cancelled",
                "Returned"
            ],
            weights=[70, 10, 8, 7, 5],
            k=1
        )[0]

        sales_channel = random.choices(
            [
                "Website",
                "Mobile App",
                "Marketplace"
            ],
            weights=[45, 40, 15],
            k=1
        )[0]

        order = {
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
        }

        orders.append(order)

    return pd.DataFrame(orders)

# ==================================================
# 8. INCREMENTAL ORDER ITEM GENERATOR
# ==================================================

def generate_incremental_order_items(
    historical_order_items: pd.DataFrame,
    historical_products: pd.DataFrame,
    new_products: pd.DataFrame,
    new_orders: pd.DataFrame
) -> pd.DataFrame:

    order_items = []

    item_id = get_next_id(
        historical_order_items,
        "order_item_id"
    )

    # Combine historical and incremental products
    all_products = pd.concat(
        [historical_products, new_products],
        ignore_index=True
    )

    all_products["created_at"] = pd.to_datetime(
        all_products["created_at"],
        utc=True,
        format="mixed"
    )

    precision = Decimal("0.01")

    for order in new_orders.to_dict("records"):

        order_date = pd.to_datetime(
            order["order_date"],
            utc=True
        )

        # Products must exist before the order date
        eligible_products = all_products[
            all_products["created_at"] <= order_date
        ]

        if eligible_products.empty:
            raise ValueError(
                f"No eligible products for {order['order_id']}"
            )

        num_items = random.choices(
            [1, 2, 3],
            weights=[30, 40, 30],
            k=1
        )[0]

        num_items = min(
            num_items,
            len(eligible_products)
        )

        selected_products = random.sample(
            eligible_products.to_dict("records"),
            k=num_items
        )

        for product in selected_products:

            quantity = random.choices(
                [1, 2, 3, 4, 5],
                weights=[60, 25, 10, 4, 1],
                k=1
            )[0]

            discount_percentage = random.choices(
                [0, 5, 10, 15, 20],
                weights=[50, 20, 15, 10, 5],
                k=1
            )[0]

            unit_price = Decimal(
                str(product["unit_price"])
            ).quantize(
                precision,
                rounding=ROUND_HALF_UP
            )

            cost_price = Decimal(
                str(product["cost_price"])
            ).quantize(
                precision,
                rounding=ROUND_HALF_UP
            )

            gross_amount = unit_price * quantity

            discount_amount = (
                gross_amount
                * Decimal(discount_percentage)
                / Decimal("100")
            ).quantize(
                precision,
                rounding=ROUND_HALF_UP
            )

            net_amount = gross_amount - discount_amount

            total_cost = cost_price * quantity

            profit_amount = net_amount - total_cost

            order_item = {
                "order_item_id": f"ITEM-{item_id:010d}",
                "order_id": order["order_id"],
                "product_id": product["product_id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "cost_price": cost_price,
                "discount_percentage": discount_percentage,
                "gross_amount": gross_amount,
                "discount_amount": discount_amount,
                "net_amount": net_amount,
                "total_cost": total_cost,
                "profit_amount": profit_amount,
                "currency": order["currency"],
                "created_at": order["order_date"],
                "updated_at": order["order_date"]
            }

            order_items.append(order_item)

            item_id += 1

    return pd.DataFrame(order_items)

# ==================================================
# 9. INCREMENTAL PAYMENT GENERATOR
# ==================================================

def generate_incremental_payments(
    historical_payments: pd.DataFrame,
    new_orders: pd.DataFrame,
    new_order_items: pd.DataFrame
) -> pd.DataFrame:

    payments = []

    start_id = get_next_id(
        historical_payments,
        "payment_id"
    )

    precision = Decimal("0.01")
    zero = Decimal("0.00")

    # Calculate total order amounts from order items
    order_totals = (
        new_order_items
        .groupby("order_id")["net_amount"]
        .sum()
        .to_dict()
    )

    for i, order in enumerate(
        new_orders.to_dict("records"),
        start=start_id
    ):

        order_id = order["order_id"]
        order_status = order["order_status"]

        order_amount = Decimal(
            str(order_totals[order_id])
        ).quantize(
            precision,
            rounding=ROUND_HALF_UP
        )

        payment_method = random.choices(
            [
                "Credit Card",
                "Debit Card",
                "Digital Wallet",
                "Bank Transfer"
            ],
            weights=[40, 25, 25, 10],
            k=1
        )[0]

        # Determine payment status
        if order_status in ["Delivered", "Shipped"]:

            payment_status = "Completed"

        elif order_status == "Returned":

            payment_status = "Refunded"

        elif order_status == "Cancelled":

            payment_status = "Failed"

        elif order_status == "Processing":

            payment_status = random.choices(
                ["Completed", "Pending"],
                weights=[70, 30],
                k=1
            )[0]

        else:

            raise ValueError(
                f"Invalid order status: {order_status}"
            )

        # Calculate payment and refund amounts
        paid_amount = zero
        refund_amount = zero

        if payment_status == "Completed":

            paid_amount = order_amount

        elif payment_status == "Refunded":

            paid_amount = order_amount
            refund_amount = order_amount

        net_payment_amount = (
            paid_amount - refund_amount
        )

        # Generate payment timestamps
        order_date = datetime.fromisoformat(
            order["order_date"]
        )

        payment_date = order_date + timedelta(
            seconds=random.randint(1, 300)
        )

        refund_date = None

        if payment_status == "Refunded":

            refund_date = payment_date + timedelta(
                days=random.randint(3, 15)
            )

        updated_at = (
            refund_date
            if refund_date is not None
            else payment_date
        )

        payment = {
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
        }

        payments.append(payment)

    return pd.DataFrame(payments)

# ==================================================
# 10. INCREMENTAL FILE WRITER
# ==================================================

import pyarrow as pa
import pyarrow.parquet as pq

ORDER_ITEMS_SCHEMA = pa.schema([
    ("order_item_id", pa.large_string()),
    ("order_id", pa.large_string()),
    ("product_id", pa.large_string()),
    ("quantity", pa.int64()),
    ("unit_price", pa.decimal128(6, 2)),
    ("cost_price", pa.decimal128(6, 2)),
    ("discount_percentage", pa.int64()),
    ("gross_amount", pa.decimal128(6, 2)),
    ("discount_amount", pa.decimal128(6, 2)),
    ("net_amount", pa.decimal128(6, 2)),
    ("total_cost", pa.decimal128(6, 2)),
    ("profit_amount", pa.decimal128(6, 2)),
    ("currency", pa.large_string()),
    ("created_at", pa.large_string()),
    ("updated_at", pa.large_string())
])

def write_incremental_data(
    entity: str,
    df: pd.DataFrame
) -> dict:

    filename = SOURCE_CONFIG[entity]["filename"]

    output_dir = (
        DATA_DIR
        / entity
        / CURRENT_BATCH
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = output_dir / filename

    # Write CSV files
    if output_path.suffix == ".csv":

        df.to_csv(
            output_path,
            index=False
        )

    # Write JSON Lines files
    elif output_path.suffix == ".json":

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            for record in df.to_dict("records"):

                file.write(
                    json.dumps(
                        record,
                        default=str,
                        ensure_ascii=False
                    ) + "\n"
                )

    # Write Parquet with explicit schema
    elif output_path.suffix == ".parquet":

        table = pa.Table.from_pandas(
            df,
            schema=ORDER_ITEMS_SCHEMA,
            preserve_index=False,
            safe=True
        )

        pq.write_table(
            table,
            output_path,
            compression="snappy"
        )

    else:

        raise ValueError(
            f"Unsupported format: {output_path.suffix}"
        )

    result = {
        "entity": entity,
        "batch_id": CURRENT_BATCH,
        "records": len(df),
        "columns": len(df.columns),
        "file_path": str(output_path),
        "file_size_bytes": output_path.stat().st_size,
        "status": "SUCCESS"
    }

    print(
        f"[SUCCESS] {entity}: "
        f"{len(df):,} records written"
    )

    print(f"File: {output_path}")

    return result

# ==================================================
# 11. MAIN EXECUTION FUNCTION
# ==================================================

def main():

    start_time = datetime.now(timezone.utc)

    print("=" * 65)
    print("COMMERCELAKE - INCREMENTAL DATA GENERATION")
    print("=" * 65)

    print(f"Previous Batch: {PREVIOUS_BATCH}")
    print(f"Current Batch: {CURRENT_BATCH}")
    print(f"Execution Started: {start_time.isoformat()}")

    # --------------------------------------------------
    # Load historical datasets
    # --------------------------------------------------

    print("\nLoading historical datasets...")

    historical_data = load_historical_data()

    for entity, df in historical_data.items():

        print(f"{entity}: {len(df):,} historical records")

    # --------------------------------------------------
    # Generate incremental datasets
    # --------------------------------------------------

    print("\nGenerating incremental customers...")

    new_customers = generate_incremental_customers(
        historical_data["customers"]
    )

    print("\nGenerating incremental products...")

    new_products = generate_incremental_products(
        historical_data["products"]
    )

    print("\nGenerating incremental orders...")

    new_orders = generate_incremental_orders(
        historical_data["orders"],
        historical_data["customers"],
        new_customers
    )

    print("\nGenerating incremental order items...")

    new_order_items = generate_incremental_order_items(
        historical_data["order_items"],
        historical_data["products"],
        new_products,
        new_orders
    )

    print("\nGenerating incremental payments...")

    new_payments = generate_incremental_payments(
        historical_data["payments"],
        new_orders,
        new_order_items
    )

    # --------------------------------------------------
    # Organize incremental datasets
    # --------------------------------------------------

    incremental_data = {
        "customers": new_customers,
        "products": new_products,
        "orders": new_orders,
        "order_items": new_order_items,
        "payments": new_payments
    }

    # --------------------------------------------------
    # Write incremental source files
    # --------------------------------------------------

    print("\nWriting incremental source files...")

    generation_results = []

    for entity, df in incremental_data.items():

        result = write_incremental_data(
            entity,
            df
        )

        generation_results.append(result)

    # --------------------------------------------------
    # Generate execution summary
    # --------------------------------------------------

    end_time = datetime.now(timezone.utc)

    duration = (
        end_time - start_time
    ).total_seconds()

    results_df = pd.DataFrame(generation_results)

    total_records = results_df["records"].sum()

    total_file_size = results_df[
        "file_size_bytes"
    ].sum()

    historical_records = sum(
        len(df)
        for df in historical_data.values()
    )

    print("\n" + "=" * 65)
    print("INCREMENTAL DATA GENERATION SUMMARY")
    print("=" * 65)

    print(
        results_df[
            [
                "entity",
                "batch_id",
                "records",
                "columns",
                "file_size_bytes",
                "status"
            ]
        ].to_string(index=False)
    )

    print("\nTotal Datasets:", len(results_df))
    print(f"Historical Records: {historical_records:,}")
    print(f"Incremental Records: {total_records:,}")

    print(
        f"Expected Cumulative Records: "
        f"{historical_records + total_records:,}"
    )

    print(f"Total File Size: {total_file_size:,} bytes")
    print(f"Execution Duration: {duration:.2f} seconds")
    print(f"Execution Completed: {end_time.isoformat()}")
    print("Generation Status: SUCCESS")

    print("=" * 65)


# ==================================================
# 12. SCRIPT ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()