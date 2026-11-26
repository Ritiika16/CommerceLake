import random
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from faker import Faker


fake = Faker("en_US")

Faker.seed(43)
random.seed(43)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "products"
    / "batch_001"
)

NUM_PRODUCTS = 200

CATEGORY_PRODUCTS = {
    "Electronics": [
        "Laptop", "Smartphone", "Headphones",
        "Monitor", "Keyboard", "Tablet"
    ],
    "Fashion": [
        "T-Shirt", "Jeans", "Jacket",
        "Sneakers", "Dress", "Handbag"
    ],
    "Home & Kitchen": [
        "Blender", "Microwave", "Cookware",
        "Coffee Maker", "Dinner Set"
    ],
    "Beauty": [
        "Shampoo", "Moisturizer", "Perfume",
        "Face Wash", "Sunscreen"
    ],
    "Sports": [
        "Yoga Mat", "Dumbbells", "Football",
        "Running Shoes", "Resistance Bands"
    ]
}

PRICE_RANGES = {
    "Electronics": (20, 2000),
    "Fashion": (10, 250),
    "Home & Kitchen": (15, 500),
    "Beauty": (5, 150),
    "Sports": (10, 400)
}

BRANDS = [
    "Nova", "Vertex", "Apex", "UrbanEdge",
    "Prime", "Zenith", "Elite", "Everest"
]


def generate_products(num_products: int) -> pd.DataFrame:

    products = []

    for i in range(1, num_products + 1):

        category = random.choice(list(CATEGORY_PRODUCTS))

        product_type = random.choice(
            CATEGORY_PRODUCTS[category]
        )

        brand = random.choice(BRANDS)

        min_price, max_price = PRICE_RANGES[category]

        unit_price = round(
            random.uniform(min_price, max_price), 2
        )

        cost_price = round(
            unit_price * random.uniform(0.40, 0.80), 2
        )

        created_at = fake.date_time_between(
            start_date=datetime(
                2023, 1, 1, tzinfo=timezone.utc
            ),
            end_date=datetime(
                2025, 12, 31, tzinfo=timezone.utc
            ),
            tzinfo=timezone.utc
        )

        products.append({
            "product_id": f"PROD-{i:07d}",
            "sku": f"SKU-{i:07d}",
            "product_name": f"{brand} {product_type}",
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
        })

    return pd.DataFrame(products)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_products(NUM_PRODUCTS)

    output_file = OUTPUT_DIR / "products.csv"

    df.to_csv(output_file, index=False)

    print("=" * 60)
    print("PRODUCT DATA GENERATION COMPLETED")
    print("=" * 60)

    print(f"Total records: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique products: {df['product_id'].nunique():,}")
    print(f"Output file: {output_file}")

    print("\nSample records:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()