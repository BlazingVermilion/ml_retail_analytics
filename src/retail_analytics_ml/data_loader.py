from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class RetailTables:
    categories: pd.DataFrame
    customers: pd.DataFrame
    exchange_rates: pd.DataFrame
    order_items: pd.DataFrame
    orders: pd.DataFrame
    products: pd.DataFrame


REQUIRED_FILES = {
    "categories": "categories.csv",
    "customers": "customers.csv",
    "exchange_rates": "exchange_rates.csv",
    "order_items": "order_items.csv",
    "orders": "orders.csv",
    "products": "products.csv",
}


def _read_csv(data_dir: Path, filename: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def load_tables(data_dir: str | Path) -> RetailTables:
    """Load the raw retail CSV tables from a directory."""
    data_path = Path(data_dir)
    return RetailTables(
        categories=_read_csv(data_path, REQUIRED_FILES["categories"]),
        customers=_read_csv(data_path, REQUIRED_FILES["customers"], parse_dates=["signup_date"]),
        exchange_rates=_read_csv(
            data_path,
            REQUIRED_FILES["exchange_rates"],
            parse_dates=["rate_date", "fetched_at"],
        ),
        order_items=_read_csv(data_path, REQUIRED_FILES["order_items"]),
        orders=_read_csv(data_path, REQUIRED_FILES["orders"], parse_dates=["order_date"]),
        products=_read_csv(data_path, REQUIRED_FILES["products"]),
    )
