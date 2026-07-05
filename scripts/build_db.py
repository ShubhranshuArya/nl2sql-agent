"""Build the Global E-Commerce & Supply Chain SQLite database from CSVs.

Reads the 8 source CSVs in ``data/`` and loads them into a fresh SQLite
database at ``backend/app/data/ecommerce.db``. Each table is created with an
explicit, primary-key-aware ``CREATE TABLE`` statement so that the agent's
schema introspection (``sqlite_master``) reflects real column types and keys,
matching ``context/data-card.md``.

Run once (idempotent): ``uv run python scripts/build_db.py`` from the repo root.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "backend" / "app" / "data" / "ecommerce.db"

# Column definitions per table, in CSV order. Types map the data-card types to
# SQLite storage classes: str/date -> TEXT, int/bool -> INTEGER, float -> REAL.
# Booleans are coerced to 0/1. The final entry per table is the PRIMARY KEY.
TABLES: dict[str, dict] = {
    "customers": {
        "columns": [
            ("customer_id", "TEXT"),
            ("first_name", "TEXT"),
            ("last_name", "TEXT"),
            ("country", "TEXT"),
            ("currency", "TEXT"),
            ("age", "INTEGER"),
            ("gender", "TEXT"),
            ("registration_date", "TEXT"),
            ("is_premium", "INTEGER"),
            ("email_verified", "INTEGER"),
            ("email", "TEXT"),
        ],
        "primary_key": ["customer_id"],
        "bool_columns": ["is_premium", "email_verified"],
    },
    "products": {
        "columns": [
            ("product_id", "TEXT"),
            ("name", "TEXT"),
            ("category", "TEXT"),
            ("brand", "TEXT"),
            ("unit_price_usd", "REAL"),
            ("unit_cost_usd", "REAL"),
            ("weight_kg", "REAL"),
            ("is_active", "INTEGER"),
            ("launch_date", "TEXT"),
        ],
        "primary_key": ["product_id"],
        "bool_columns": ["is_active"],
    },
    "transactions": {
        "columns": [
            ("transaction_id", "TEXT"),
            ("customer_id", "TEXT"),
            ("product_id", "TEXT"),
            ("date", "TEXT"),
            ("quantity", "INTEGER"),
            ("unit_price_usd", "REAL"),
            ("discount_pct", "REAL"),
            ("revenue_usd", "REAL"),
            ("cost_usd", "REAL"),
            ("profit_usd", "REAL"),
            ("shipping_cost_usd", "REAL"),
            ("channel", "TEXT"),
            ("payment_method", "TEXT"),
            ("status", "TEXT"),
            ("country", "TEXT"),
            ("category", "TEXT"),
        ],
        "primary_key": ["transaction_id"],
        "bool_columns": [],
    },
    "returns": {
        "columns": [
            ("return_id", "TEXT"),
            ("transaction_id", "TEXT"),
            ("customer_id", "TEXT"),
            ("product_id", "TEXT"),
            ("return_date", "TEXT"),
            ("reason", "TEXT"),
            ("refund_amount_usd", "REAL"),
            ("restocked", "INTEGER"),
        ],
        "primary_key": ["return_id"],
        "bool_columns": ["restocked"],
    },
    "inventory": {
        "columns": [
            ("product_id", "TEXT"),
            ("category", "TEXT"),
            ("stock_units", "INTEGER"),
            ("reorder_point", "INTEGER"),
            ("warehouse_location", "TEXT"),
            ("last_restock_date", "TEXT"),
            ("supplier_lead_days", "INTEGER"),
        ],
        "primary_key": ["product_id"],
        "bool_columns": [],
    },
    "price_history": {
        "columns": [
            ("product_id", "TEXT"),
            ("category", "TEXT"),
            ("year_month", "TEXT"),
            ("listed_price_usd", "REAL"),
            ("base_price_usd", "REAL"),
            ("competitor_price_usd", "REAL"),
            ("price_index", "REAL"),
            ("is_promotional", "INTEGER"),
            ("price_elasticity", "REAL"),
            ("units_sold", "INTEGER"),
            ("revenue_usd", "REAL"),
            ("margin_pct", "REAL"),
        ],
        "primary_key": ["product_id", "year_month"],
        "bool_columns": ["is_promotional"],
    },
    "supplier_costs": {
        "columns": [
            ("product_id", "TEXT"),
            ("category", "TEXT"),
            ("supplier_name", "TEXT"),
            ("supplier_rank", "INTEGER"),
            ("unit_cost_usd", "REAL"),
            ("ordering_cost_usd", "REAL"),
            ("annual_holding_cost_usd", "REAL"),
            ("holding_cost_pct", "REAL"),
            ("lead_time_days", "INTEGER"),
            ("min_order_qty", "INTEGER"),
            ("reliability_score", "REAL"),
            ("is_primary", "INTEGER"),
        ],
        "primary_key": ["product_id", "supplier_name"],
        "bool_columns": ["is_primary"],
    },
    "marketing_spend": {
        "columns": [
            ("year_month", "TEXT"),
            ("channel", "TEXT"),
            ("spend_usd", "REAL"),
            ("impressions", "INTEGER"),
            ("clicks", "INTEGER"),
            ("ctr", "REAL"),
            ("actual_orders", "INTEGER"),
            ("actual_customers", "INTEGER"),
            ("actual_revenue_usd", "REAL"),
            ("roas", "REAL"),
            ("cac_usd", "REAL"),
            ("cost_per_order_usd", "REAL"),
            ("month_multiplier", "REAL"),
        ],
        "primary_key": ["year_month", "channel"],
        "bool_columns": [],
    },
}


def build_create_statement(table_name: str, spec: dict) -> str:
    """Construct an explicit CREATE TABLE statement with a PRIMARY KEY."""
    col_defs = [f'    "{name}" {sql_type}' for name, sql_type in spec["columns"]]
    pk_cols = ", ".join(f'"{c}"' for c in spec["primary_key"])
    col_defs.append(f"    PRIMARY KEY ({pk_cols})")
    body = ",\n".join(col_defs)
    return f'CREATE TABLE "{table_name}" (\n{body}\n);'


def coerce_booleans(df: pd.DataFrame, bool_columns: list[str]) -> pd.DataFrame:
    """Convert 'True'/'False' (string or bool) columns into 0/1 integers."""
    for col in bool_columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": 1, "false": 0, "1": 1, "0": 0})
            .astype("Int64")
        )
    return df


def main() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        summary: list[tuple[str, int]] = []
        for table_name, spec in TABLES.items():
            csv_path = DATA_DIR / f"{table_name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing CSV for '{table_name}': {csv_path}")

            expected_cols = [name for name, _ in spec["columns"]]
            df = pd.read_csv(csv_path)

            missing = set(expected_cols) - set(df.columns)
            if missing:
                raise ValueError(
                    f"CSV '{csv_path.name}' is missing columns: {sorted(missing)}"
                )

            # Keep only expected columns, in the declared order.
            df = df[expected_cols]
            df = coerce_booleans(df, spec["bool_columns"])

            conn.execute(build_create_statement(table_name, spec))
            df.to_sql(table_name, conn, if_exists="append", index=False)

            summary.append((table_name, len(df)))

        conn.commit()
    finally:
        conn.close()

    print(f"\nBuilt database at: {DB_PATH}\n")
    print(f"{'Table':<18}{'Rows':>10}")
    print("-" * 28)
    for name, count in summary:
        print(f"{name:<18}{count:>10,}")


if __name__ == "__main__":
    main()
