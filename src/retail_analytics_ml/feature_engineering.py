from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from retail_analytics_ml.data_loader import RetailTables

SUPPORTED_CURRENCIES = ("USD", "GBP", "INR")


def build_sales_fact(tables: RetailTables) -> pd.DataFrame:
    """Create an analysis-ready order-line fact table with dimensions and currency columns.

    The source unit_price is treated as EUR. Exchange-rate columns are joined by order_date.
    """
    order_lines = (
        tables.order_items.merge(tables.orders, on="order_id", how="left")
        .merge(tables.products, on="product_id", how="left", suffixes=("_item", "_product"))
        .merge(tables.categories, on="category_id", how="left")
        .merge(tables.customers, on="customer_id", how="left")
    )
    order_lines["line_revenue_eur"] = order_lines["quantity"] * order_lines["unit_price_item"]
    order_lines["line_cost_eur"] = order_lines["quantity"] * order_lines["cost_price"]
    order_lines["line_profit_eur"] = order_lines["line_revenue_eur"] - order_lines["line_cost_eur"]

    exchange_rates = tables.exchange_rates.copy()
    exchange_rates["target_currency"] = exchange_rates["target_currency"].str.upper()
    exchange_pivot = (
        exchange_rates[exchange_rates["target_currency"].isin(SUPPORTED_CURRENCIES)]
        .pivot_table(index="rate_date", columns="target_currency", values="rate", aggfunc="last")
        .reset_index()
        .rename(columns={currency: f"rate_{currency.lower()}" for currency in SUPPORTED_CURRENCIES})
    )

    fact = order_lines.merge(exchange_pivot, left_on="order_date", right_on="rate_date", how="left")
    for currency in SUPPORTED_CURRENCIES:
        rate_col = f"rate_{currency.lower()}"
        revenue_col = f"line_revenue_{currency.lower()}"
        fact[revenue_col] = fact["line_revenue_eur"] * fact[rate_col]

    fact["order_year"] = fact["order_date"].dt.year
    fact["order_month"] = fact["order_date"].dt.month
    fact["order_quarter"] = fact["order_date"].dt.quarter
    fact["order_day_of_week"] = fact["order_date"].dt.dayofweek
    fact["is_weekend"] = fact["order_day_of_week"].isin([5, 6]).astype(int)

    return fact.sort_values(["order_date", "order_id", "order_item_id"]).reset_index(drop=True)


def build_daily_revenue_features(sales_fact: pd.DataFrame) -> pd.DataFrame:
    """Aggregate order-line data into a daily ML feature table for forecasting."""
    daily = (
        sales_fact.groupby("order_date")
        .agg(
            revenue_eur=("line_revenue_eur", "sum"),
            order_count=("order_id", "nunique"),
            item_quantity=("quantity", "sum"),
            avg_order_value_eur=("line_revenue_eur", lambda s: s.sum()),
            unique_customers=("customer_id", "nunique"),
            unique_products=("product_id", "nunique"),
        )
        .reset_index()
        .sort_values("order_date")
    )
    daily["avg_order_value_eur"] = daily["revenue_eur"] / daily["order_count"].replace(0, np.nan)

    full_dates = pd.date_range(daily["order_date"].min(), daily["order_date"].max(), freq="D")
    daily = (
        daily.set_index("order_date").reindex(full_dates).rename_axis("order_date").reset_index()
    )
    fill_zero_cols = [
        "revenue_eur",
        "order_count",
        "item_quantity",
        "unique_customers",
        "unique_products",
    ]
    daily[fill_zero_cols] = daily[fill_zero_cols].fillna(0)
    daily["avg_order_value_eur"] = daily["avg_order_value_eur"].fillna(0)

    daily["day_of_week"] = daily["order_date"].dt.dayofweek
    daily["month"] = daily["order_date"].dt.month
    daily["quarter"] = daily["order_date"].dt.quarter
    daily["day_of_month"] = daily["order_date"].dt.day
    daily["is_weekend"] = daily["day_of_week"].isin([5, 6]).astype(int)

    for lag in (1, 7, 14, 30):
        daily[f"revenue_lag_{lag}"] = daily["revenue_eur"].shift(lag)

    for window in (7, 14, 30):
        daily[f"revenue_rolling_mean_{window}"] = (
            daily["revenue_eur"].shift(1).rolling(window).mean()
        )
        daily[f"order_rolling_mean_{window}"] = daily["order_count"].shift(1).rolling(window).mean()

    return daily.fillna(0)


def build_customer_features(
    sales_fact: pd.DataFrame, reference_date: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Build customer-level RFM and behavior features for segmentation."""
    if reference_date is None:
        reference_date = sales_fact["order_date"].max() + pd.Timedelta(days=1)

    customer = (
        sales_fact.groupby("customer_id")
        .agg(
            first_name=("first_name", "first"),
            last_name=("last_name", "first"),
            country=("country", "first"),
            city=("city", "first"),
            signup_date=("signup_date", "first"),
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            frequency=("order_id", "nunique"),
            monetary_eur=("line_revenue_eur", "sum"),
            total_quantity=("quantity", "sum"),
            unique_products=("product_id", "nunique"),
            unique_categories=("category_id", "nunique"),
            gross_profit_eur=("line_profit_eur", "sum"),
        )
        .reset_index()
    )
    customer["customer_name"] = customer["first_name"] + " " + customer["last_name"]
    customer["recency_days"] = (reference_date - customer["last_order_date"]).dt.days
    customer["customer_tenure_days"] = (reference_date - customer["signup_date"]).dt.days
    customer["avg_order_value_eur"] = customer["monetary_eur"] / customer["frequency"].replace(
        0, np.nan
    )
    customer["profit_margin"] = customer["gross_profit_eur"] / customer["monetary_eur"].replace(
        0, np.nan
    )

    favorite_category = (
        sales_fact.groupby(["customer_id", "category_name"])["line_revenue_eur"]
        .sum()
        .reset_index()
        .sort_values(["customer_id", "line_revenue_eur"], ascending=[True, False])
        .drop_duplicates("customer_id")
        .rename(
            columns={
                "category_name": "favorite_category",
                "line_revenue_eur": "favorite_category_revenue_eur",
            }
        )
    )
    customer = customer.merge(favorite_category, on="customer_id", how="left")
    return customer.fillna(0)


def write_core_datasets(data_dir: str | Path, output_dir: str | Path) -> dict[str, Path]:
    """Build and persist fact, daily, and customer feature datasets."""
    from retail_analytics_ml.data_loader import load_tables

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tables = load_tables(data_dir)
    sales_fact = build_sales_fact(tables)
    daily_features = build_daily_revenue_features(sales_fact)
    customer_features = build_customer_features(sales_fact)

    paths = {
        "sales_fact": output_path / "sales_fact_multicurrency.csv",
        "daily_features": output_path / "daily_revenue_features.csv",
        "customer_features": output_path / "customer_features_rfm.csv",
    }
    sales_fact.to_csv(paths["sales_fact"], index=False)
    daily_features.to_csv(paths["daily_features"], index=False)
    customer_features.to_csv(paths["customer_features"], index=False)
    return paths
