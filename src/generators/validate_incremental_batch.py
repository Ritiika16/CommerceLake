import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import pyarrow.parquet as pq


# ==================================================
# 1. VALIDATION CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "generated"

HISTORICAL_BATCH = "batch_001"
INCREMENTAL_BATCH = "batch_002"

SOURCE_CONFIG = {
    "customers": {
        "filename": "customers.csv",
        "primary_key": "customer_id",
        "historical_count": 1000,
        "incremental_count": 200,
        "expected_columns": 13
    },
    "products": {
        "filename": "products.csv",
        "primary_key": "product_id",
        "historical_count": 200,
        "incremental_count": 50,
        "expected_columns": 12
    },
    "orders": {
        "filename": "orders.json",
        "primary_key": "order_id",
        "historical_count": 5000,
        "incremental_count": 1000,
        "expected_columns": 11
    },
    "order_items": {
        "filename": "order_items.parquet",
        "primary_key": "order_item_id",
        "historical_count": 10055,
        "incremental_count": 1969,
        "expected_columns": 15
    },
    "payments": {
        "filename": "payments.json",
        "primary_key": "payment_id",
        "historical_count": 5000,
        "incremental_count": 1000,
        "expected_columns": 13
    }
}

EXPECTED_INCREMENTAL_RECORDS = 4219
EXPECTED_CUMULATIVE_RECORDS = 25474

VALIDATION_RESULTS = []


# ==================================================
# 2. SOURCE FILE LOADER
# ==================================================

def load_source_file(
    entity: str,
    batch_id: str
) -> pd.DataFrame:

    file_path = (
        DATA_DIR
        / entity
        / batch_id
        / SOURCE_CONFIG[entity]["filename"]
    )

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Source file not found: {file_path}"
        )

    if file_path.stat().st_size == 0:
        raise ValueError(
            f"Empty source file: {file_path}"
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
            f"Unsupported format: {file_path.suffix}"
        )

    return df


# ==================================================
# 3. LOAD COMPLETE BATCH
# ==================================================

def load_batch(batch_id: str) -> dict:

    datasets = {}

    print(f"\nLoading batch: {batch_id}")

    for entity in SOURCE_CONFIG:

        df = load_source_file(
            entity,
            batch_id
        )

        datasets[entity] = df

        print(
            f"{entity}: "
            f"{len(df):,} records | "
            f"{len(df.columns)} columns"
        )

    return datasets


# ==================================================
# 4. REUSABLE VALIDATION RESULT RECORDER
# ==================================================

def record_validation(
    entity: str,
    check_name: str,
    violation_count: int
):

    violation_count = int(violation_count)

    status = (
        "PASS"
        if violation_count == 0
        else "FAIL"
    )

    result = {
        "entity": entity,
        "check_name": check_name,
        "violation_count": violation_count,
        "status": status
    }

    VALIDATION_RESULTS.append(result)

    print(
        f"[{status}] {entity} | "
        f"{check_name} | "
        f"Violations: {violation_count:,}"
    )

    return result

# ==================================================
# 5. BASIC DATASET VALIDATION
# ==================================================

def validate_basic_datasets(
    historical_data: dict,
    incremental_data: dict
):

    print("\n" + "=" * 65)
    print("BASIC DATASET VALIDATION")
    print("=" * 65)

    for entity, config in SOURCE_CONFIG.items():

        historical_df = historical_data[entity]
        incremental_df = incremental_data[entity]

        primary_key = config["primary_key"]

        print(f"\nValidating {entity}...")

        # 1. Historical record count
        record_validation(
            entity,
            "Historical record count",
            abs(
                len(historical_df)
                - config["historical_count"]
            )
        )

        # 2. Incremental record count
        record_validation(
            entity,
            "Incremental record count",
            abs(
                len(incremental_df)
                - config["incremental_count"]
            )
        )

        # 3. Expected column count
        record_validation(
            entity,
            "Expected column count",
            abs(
                len(incremental_df.columns)
                - config["expected_columns"]
            )
        )

        # 4. Column names and order compatibility
        record_validation(
            entity,
            "Column schema compatibility",
            int(
                list(historical_df.columns)
                != list(incremental_df.columns)
            )
        )

        # 5. Duplicate records
        record_validation(
            entity,
            "Duplicate records",
            incremental_df.duplicated().sum()
        )

        # 6. Duplicate primary keys
        record_validation(
            entity,
            "Duplicate primary keys",
            incremental_df[primary_key].duplicated().sum()
        )

        # 7. Null primary keys
        record_validation(
            entity,
            "Null primary keys",
            incremental_df[primary_key].isna().sum()
        )

        # 8. Cross-batch primary key collisions
        record_validation(
            entity,
            "Cross-batch primary key collisions",
            incremental_df[primary_key].isin(
                historical_df[primary_key]
            ).sum()
        )

        # 9. Unexpected null values
        required_columns = [
            column
            for column in incremental_df.columns
            if not (
                entity == "payments"
                and column == "refund_date"
            )
        ]

        record_validation(
            entity,
            "Unexpected null values",
            incremental_df[
                required_columns
            ].isna().sum().sum()
        )

        # 10. Product SKU uniqueness
        if entity == "products":

            record_validation(
                entity,
                "Duplicate SKUs",
                incremental_df["sku"].duplicated().sum()
            )

            record_validation(
                entity,
                "Cross-batch SKU collisions",
                incremental_df["sku"].isin(
                    historical_df["sku"]
                ).sum()
            )

        # 11. Customer email uniqueness
        if entity == "customers":

            record_validation(
                entity,
                "Duplicate customer emails",
                incremental_df["email"].duplicated().sum()
            )

            record_validation(
                entity,
                "Cross-batch email collisions",
                incremental_df["email"].isin(
                    historical_df["email"]
                ).sum()
            )


# ==================================================
# 6. PARQUET SCHEMA VALIDATION
# ==================================================

def validate_parquet_schema():

    historical_path = (
        DATA_DIR
        / "order_items"
        / HISTORICAL_BATCH
        / "order_items.parquet"
    )

    incremental_path = (
        DATA_DIR
        / "order_items"
        / INCREMENTAL_BATCH
        / "order_items.parquet"
    )

    historical_schema = pq.read_schema(
        historical_path
    )

    incremental_schema = pq.read_schema(
        incremental_path
    )

    record_validation(
        "order_items",
        "Parquet schema compatibility",
        int(
            not historical_schema.equals(
                incremental_schema,
                check_metadata=False
            )
        )
    )

# ==================================================
# 7. REFERENTIAL INTEGRITY VALIDATION
# ==================================================

def validate_referential_integrity(
    historical_data: dict,
    incremental_data: dict
):

    print("\n" + "=" * 65)
    print("REFERENTIAL INTEGRITY VALIDATION")
    print("=" * 65)

    all_customers = pd.concat(
        [
            historical_data["customers"],
            incremental_data["customers"]
        ],
        ignore_index=True
    )

    all_products = pd.concat(
        [
            historical_data["products"],
            incremental_data["products"]
        ],
        ignore_index=True
    )

    new_orders = incremental_data["orders"]
    new_order_items = incremental_data["order_items"]
    new_payments = incremental_data["payments"]

    # 1. Orders must reference valid customers
    record_validation(
        "orders",
        "Orphan customer references",
        (
            ~new_orders["customer_id"].isin(
                all_customers["customer_id"]
            )
        ).sum()
    )

    # 2. Order items must reference new orders
    record_validation(
        "order_items",
        "Orphan order references",
        (
            ~new_order_items["order_id"].isin(
                new_orders["order_id"]
            )
        ).sum()
    )

    # 3. Order items must reference valid products
    record_validation(
        "order_items",
        "Orphan product references",
        (
            ~new_order_items["product_id"].isin(
                all_products["product_id"]
            )
        ).sum()
    )

    # 4. Payments must reference new orders
    record_validation(
        "payments",
        "Orphan order references",
        (
            ~new_payments["order_id"].isin(
                new_orders["order_id"]
            )
        ).sum()
    )

    # 5. Every new order must contain order items
    record_validation(
        "orders",
        "Orders without order items",
        (
            ~new_orders["order_id"].isin(
                new_order_items["order_id"]
            )
        ).sum()
    )

    # 6. Every new order must have a payment
    record_validation(
        "orders",
        "Orders without payments",
        (
            ~new_orders["order_id"].isin(
                new_payments["order_id"]
            )
        ).sum()
    )

    # 7. One payment record per order
    record_validation(
        "payments",
        "Multiple payments per order",
        new_payments["order_id"].duplicated().sum()
    )

    # 8. No repeated products within an order
    record_validation(
        "order_items",
        "Duplicate products within orders",
        new_order_items.duplicated(
            subset=["order_id", "product_id"]
        ).sum()
    )


# ==================================================
# 8. TEMPORAL INTEGRITY VALIDATION
# ==================================================

def validate_temporal_integrity(
    historical_data: dict,
    incremental_data: dict
):

    print("\n" + "=" * 65)
    print("TEMPORAL INTEGRITY VALIDATION")
    print("=" * 65)

    all_customers = pd.concat(
        [
            historical_data["customers"],
            incremental_data["customers"]
        ],
        ignore_index=True
    )

    all_products = pd.concat(
        [
            historical_data["products"],
            incremental_data["products"]
        ],
        ignore_index=True
    )

    new_orders = incremental_data["orders"].copy()
    new_order_items = incremental_data["order_items"].copy()
    new_payments = incremental_data["payments"].copy()

    # Convert timestamps for comparison
    all_customers["created_at"] = pd.to_datetime(
        all_customers["created_at"],
        utc=True,
        format="mixed"
    )

    all_products["created_at"] = pd.to_datetime(
        all_products["created_at"],
        utc=True,
        format="mixed"
    )

    new_orders["order_date"] = pd.to_datetime(
        new_orders["order_date"],
        utc=True,
        format="mixed"
    )

    new_payments["payment_date"] = pd.to_datetime(
        new_payments["payment_date"],
        utc=True,
        format="mixed"
    )

    new_payments["refund_date"] = pd.to_datetime(
        new_payments["refund_date"],
        utc=True,
        format="mixed"
    )

    # 1. Orders cannot precede customer registration
    customer_orders = new_orders.merge(
        all_customers[
            ["customer_id", "created_at"]
        ].rename(
            columns={
                "created_at": "customer_created_at"
            }
        ),
        on="customer_id",
        how="left"
    )

    record_validation(
        "orders",
        "Orders before customer registration",
        (
            customer_orders["order_date"]
            < customer_orders["customer_created_at"]
        ).sum()
    )

    # 2. Products must exist before purchase
    product_orders = new_order_items.merge(
        all_products[
            ["product_id", "created_at"]
        ].rename(
            columns={
                "created_at": "product_created_at"
            }
        ),
        on="product_id",
        how="left"
    ).merge(
        new_orders[
            ["order_id", "order_date"]
        ],
        on="order_id",
        how="left"
    )

    record_validation(
        "order_items",
        "Orders before product creation",
        (
            product_orders["order_date"]
            < product_orders["product_created_at"]
        ).sum()
    )

    # 3. Payments cannot precede orders
    payment_orders = new_payments.merge(
        new_orders[
            ["order_id", "order_date"]
        ],
        on="order_id",
        how="left"
    )

    record_validation(
        "payments",
        "Payments before order placement",
        (
            payment_orders["payment_date"]
            < payment_orders["order_date"]
        ).sum()
    )

    # 4. Refunds cannot precede payments
    refunded_payments = new_payments[
        new_payments["refund_date"].notna()
    ]

    record_validation(
        "payments",
        "Refunds before payment",
        (
            refunded_payments["refund_date"]
            < refunded_payments["payment_date"]
        ).sum()
    )

    # 5. New orders must belong to January 2026
    batch_start = pd.Timestamp(
        "2026-01-01",
        tz="UTC"
    )

    batch_end = pd.Timestamp(
        "2026-02-01",
        tz="UTC"
    )

    record_validation(
        "orders",
        "Orders outside incremental batch period",
        (
            (new_orders["order_date"] < batch_start)
            | (new_orders["order_date"] >= batch_end)
        ).sum()
    )

    # 6. Updated timestamps cannot precede creation
    for entity, df in incremental_data.items():

        created_at = pd.to_datetime(
            df["created_at"],
            utc=True,
            format="mixed"
        )

        updated_at = pd.to_datetime(
            df["updated_at"],
            utc=True,
            format="mixed"
        )

        record_validation(
            entity,
            "Updates before record creation",
            (updated_at < created_at).sum()
        )

# ==================================================
# 9. FINANCIAL CALCULATION VALIDATION
# ==================================================

def validate_financial_calculations(
    incremental_data: dict
):

    print("\n" + "=" * 65)
    print("FINANCIAL CALCULATION VALIDATION")
    print("=" * 65)

    products = incremental_data["products"].copy()
    items = incremental_data["order_items"].copy()

    precision = Decimal("0.01")

    # 1. Valid product selling prices
    record_validation(
        "products",
        "Invalid selling prices",
        (products["unit_price"] <= 0).sum()
    )

    # 2. Valid product cost prices
    record_validation(
        "products",
        "Invalid cost prices",
        (
            (products["cost_price"] <= 0)
            | (
                products["cost_price"]
                > products["unit_price"]
            )
        ).sum()
    )

    # 3. Valid stock quantities
    record_validation(
        "products",
        "Negative stock quantities",
        (products["stock_quantity"] < 0).sum()
    )

    # 4. Valid order item quantities
    record_validation(
        "order_items",
        "Invalid quantities",
        (~items["quantity"].between(1, 5)).sum()
    )

    # 5. Valid discount percentages
    record_validation(
        "order_items",
        "Invalid discount percentages",
        (
            ~items["discount_percentage"].isin(
                [0, 5, 10, 15, 20]
            )
        ).sum()
    )

    # 6. Validate gross amount
    expected_gross = (
        items["unit_price"] * items["quantity"]
    )

    record_validation(
        "order_items",
        "Gross amount mismatches",
        (items["gross_amount"] != expected_gross).sum()
    )

    # 7. Validate discount amount
    expected_discount = items.apply(
        lambda row: (
            row["gross_amount"]
            * Decimal(str(row["discount_percentage"]))
            / Decimal("100")
        ).quantize(
            precision,
            rounding=ROUND_HALF_UP
        ),
        axis=1
    )

    record_validation(
        "order_items",
        "Discount amount mismatches",
        (
            items["discount_amount"]
            != expected_discount
        ).sum()
    )

    # 8. Validate net amount
    expected_net = (
        items["gross_amount"]
        - items["discount_amount"]
    )

    record_validation(
        "order_items",
        "Net amount mismatches",
        (items["net_amount"] != expected_net).sum()
    )

    # 9. Validate total cost
    expected_cost = (
        items["cost_price"] * items["quantity"]
    )

    record_validation(
        "order_items",
        "Total cost mismatches",
        (items["total_cost"] != expected_cost).sum()
    )

    # 10. Validate profit amount
    expected_profit = (
        items["net_amount"] - items["total_cost"]
    )

    record_validation(
        "order_items",
        "Profit amount mismatches",
        (
            items["profit_amount"]
            != expected_profit
        ).sum()
    )

    # 11. Validate non-negative net amounts
    record_validation(
        "order_items",
        "Negative net amounts",
        (items["net_amount"] < Decimal("0.00")).sum()
    )


# ==================================================
# 10. PAYMENT RECONCILIATION VALIDATION
# ==================================================

def validate_payment_reconciliation(
    incremental_data: dict
):

    print("\n" + "=" * 65)
    print("PAYMENT RECONCILIATION VALIDATION")
    print("=" * 65)

    orders = incremental_data["orders"].copy()
    items = incremental_data["order_items"].copy()
    payments = incremental_data["payments"].copy()

    zero = Decimal("0.00")

    monetary_columns = [
        "order_amount",
        "paid_amount",
        "refund_amount",
        "net_payment_amount"
    ]

    # Convert JSON monetary strings to Decimal
    for column in monetary_columns:

        payments[column] = payments[column].apply(
            lambda value: Decimal(str(value))
        )

    # Calculate expected order totals
    order_totals = (
        items.groupby("order_id")["net_amount"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "net_amount": "expected_order_amount"
            }
        )
    )

    reconciled = payments.merge(
        order_totals,
        on="order_id",
        how="left"
    ).merge(
        orders[["order_id", "order_status"]],
        on="order_id",
        how="left"
    )

    # 1. Reconcile order amount with order items
    record_validation(
        "payments",
        "Order amount reconciliation mismatches",
        (
            reconciled["order_amount"]
            != reconciled["expected_order_amount"]
        ).sum()
    )

    # 2. Validate net payment calculation
    record_validation(
        "payments",
        "Net payment calculation mismatches",
        (
            payments["net_payment_amount"]
            != (
                payments["paid_amount"]
                - payments["refund_amount"]
            )
        ).sum()
    )

    # 3. Validate payment statuses
    record_validation(
        "payments",
        "Invalid payment statuses",
        (
            ~payments["payment_status"].isin(
                [
                    "Completed",
                    "Refunded",
                    "Failed",
                    "Pending"
                ]
            )
        ).sum()
    )

    # 4. Validate payment methods
    record_validation(
        "payments",
        "Invalid payment methods",
        (
            ~payments["payment_method"].isin(
                [
                    "Credit Card",
                    "Debit Card",
                    "Digital Wallet",
                    "Bank Transfer"
                ]
            )
        ).sum()
    )

    # 5. Validate order-to-payment status mapping
    allowed_statuses = {
        "Delivered": {"Completed"},
        "Shipped": {"Completed"},
        "Returned": {"Refunded"},
        "Cancelled": {"Failed"},
        "Processing": {"Completed", "Pending"}
    }

    invalid_status_mapping = reconciled.apply(
        lambda row: (
            row["payment_status"]
            not in allowed_statuses.get(
                row["order_status"],
                set()
            )
        ),
        axis=1
    )

    record_validation(
        "payments",
        "Order-payment status mismatches",
        invalid_status_mapping.sum()
    )

    # 6. Completed payment validation
    completed = payments[
        payments["payment_status"] == "Completed"
    ]

    record_validation(
        "payments",
        "Invalid completed payments",
        (
            (
                completed["paid_amount"]
                != completed["order_amount"]
            )
            | (completed["refund_amount"] != zero)
        ).sum()
    )

    # 7. Refunded payment validation
    refunded = payments[
        payments["payment_status"] == "Refunded"
    ]

    record_validation(
        "payments",
        "Invalid refunded payments",
        (
            (
                refunded["paid_amount"]
                != refunded["order_amount"]
            )
            | (
                refunded["refund_amount"]
                != refunded["order_amount"]
            )
            | (refunded["net_payment_amount"] != zero)
        ).sum()
    )

    # 8. Failed and pending payment validation
    unpaid = payments[
        payments["payment_status"].isin(
            ["Failed", "Pending"]
        )
    ]

    record_validation(
        "payments",
        "Invalid failed or pending payments",
        (
            (unpaid["paid_amount"] != zero)
            | (unpaid["refund_amount"] != zero)
            | (unpaid["net_payment_amount"] != zero)
        ).sum()
    )

    # 9. Validate refund amount limits
    record_validation(
        "payments",
        "Refund amount exceeds paid amount",
        (
            payments["refund_amount"]
            > payments["paid_amount"]
        ).sum()
    )

    # 10. Validate refund date consistency
    record_validation(
        "payments",
        "Refund date inconsistencies",
        (
            (
                payments["payment_status"].eq("Refunded")
                & payments["refund_date"].isna()
            )
            | (
                payments["payment_status"].ne("Refunded")
                & payments["refund_date"].notna()
            )
        ).sum()
    )

    # 11. Validate non-negative monetary amounts
    record_validation(
        "payments",
        "Negative monetary amounts",
        (
            payments[monetary_columns] < zero
        ).sum().sum()
    )

    # --------------------------------------------------
    # Financial reconciliation summary
    # --------------------------------------------------

    total_item_amount = items["net_amount"].sum()

    total_order_amount = payments["order_amount"].sum()

    total_paid = payments["paid_amount"].sum()

    total_refunded = payments["refund_amount"].sum()

    total_net_payment = payments[
        "net_payment_amount"
    ].sum()

    # 12. Aggregate order reconciliation
    record_validation(
        "payments",
        "Aggregate order amount mismatch",
        int(total_item_amount != total_order_amount)
    )

    # 13. Aggregate payment reconciliation
    record_validation(
        "payments",
        "Aggregate net payment mismatch",
        int(
            total_net_payment
            != total_paid - total_refunded
        )
    )

    print("\nFINANCIAL RECONCILIATION SUMMARY")

    print(f"Total Item Amount: ${total_item_amount:,.2f}")
    print(f"Total Order Amount: ${total_order_amount:,.2f}")
    print(f"Total Paid Amount: ${total_paid:,.2f}")
    print(f"Total Refunded Amount: ${total_refunded:,.2f}")
    print(f"Total Net Payment: ${total_net_payment:,.2f}")

# ==================================================
# 11. FINAL VALIDATION SUMMARY
# ==================================================

def generate_validation_summary():

    results_df = pd.DataFrame(VALIDATION_RESULTS)

    total_checks = len(results_df)

    passed_checks = (
        results_df["status"] == "PASS"
    ).sum()

    failed_checks = (
        results_df["status"] == "FAIL"
    ).sum()

    total_violations = results_df[
        "violation_count"
    ].sum()

    success_rate = (
        passed_checks / total_checks * 100
        if total_checks > 0
        else 0
    )

    print("\n" + "=" * 65)
    print("COMMERCELAKE - FINAL VALIDATION SUMMARY")
    print("=" * 65)

    print("\nDATASET-WISE VALIDATION RESULTS")

    entity_summary = (
        results_df.groupby("entity")
        .agg(
            total_checks=("check_name", "count"),
            passed_checks=(
                "status",
                lambda values: (values == "PASS").sum()
            ),
            failed_checks=(
                "status",
                lambda values: (values == "FAIL").sum()
            ),
            total_violations=("violation_count", "sum")
        )
        .reset_index()
    )

    print(entity_summary.to_string(index=False))

    print("\nOVERALL VALIDATION METRICS")

    print(f"Total Validation Checks: {total_checks}")
    print(f"Passed Checks: {passed_checks}")
    print(f"Failed Checks: {failed_checks}")
    print(f"Total Violations: {total_violations}")
    print(f"Validation Success Rate: {success_rate:.2f}%")

    if failed_checks > 0:

        print("\nFAILED VALIDATION CHECKS")

        failed_results = results_df[
            results_df["status"] == "FAIL"
        ]

        print(failed_results.to_string(index=False))

        print("\nValidation Status: FAILED")
        print("Batch is NOT ready for ingestion.")

        raise SystemExit(1)

    print("\nValidation Status: SUCCESS")
    print("Batch is ready for Databricks ingestion.")

    print("=" * 65)


# ==================================================
# 12. MAIN EXECUTION FUNCTION
# ==================================================

def main():

    VALIDATION_RESULTS.clear()

    print("=" * 65)
    print("COMMERCELAKE - INCREMENTAL BATCH VALIDATION")
    print("=" * 65)

    print(f"Historical Batch: {HISTORICAL_BATCH}")
    print(f"Incremental Batch: {INCREMENTAL_BATCH}")

    # Load historical and incremental datasets
    historical_data = load_batch(
        HISTORICAL_BATCH
    )

    incremental_data = load_batch(
        INCREMENTAL_BATCH
    )

    # Execute all validation categories
    validate_basic_datasets(
        historical_data,
        incremental_data
    )

    validate_parquet_schema()

    validate_referential_integrity(
        historical_data,
        incremental_data
    )

    validate_temporal_integrity(
        historical_data,
        incremental_data
    )

    validate_financial_calculations(
        incremental_data
    )

    validate_payment_reconciliation(
        incremental_data
    )

    # --------------------------------------------------
    # Batch-level record count reconciliation
    # --------------------------------------------------

    historical_records = sum(
        len(df)
        for df in historical_data.values()
    )

    incremental_records = sum(
        len(df)
        for df in incremental_data.values()
    )

    cumulative_records = (
        historical_records + incremental_records
    )

    print("\n" + "=" * 65)
    print("BATCH RECORD COUNT RECONCILIATION")
    print("=" * 65)

    record_validation(
        "batch",
        "Total incremental record count",
        abs(
            incremental_records
            - EXPECTED_INCREMENTAL_RECORDS
        )
    )

    record_validation(
        "batch",
        "Total cumulative record count",
        abs(
            cumulative_records
            - EXPECTED_CUMULATIVE_RECORDS
        )
    )

    print(f"\nHistorical Records: {historical_records:,}")
    print(f"Incremental Records: {incremental_records:,}")
    print(f"Cumulative Records: {cumulative_records:,}")

    # Generate final report
    generate_validation_summary()


# ==================================================
# 13. SCRIPT ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()