from pathlib import Path

from retail_analytics_ml.data_loader import load_tables
from retail_analytics_ml.feature_engineering import (
    build_customer_features,
    build_daily_revenue_features,
    build_sales_fact,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_load_tables():
    tables = load_tables(DATA_DIR)
    assert len(tables.orders) == 200
    assert len(tables.order_items) == 400
    assert len(tables.customers) == 20


def test_sales_fact_matches_powerbi_kpis():
    tables = load_tables(DATA_DIR)
    sales_fact = build_sales_fact(tables)
    assert round(float(sales_fact["line_revenue_eur"].sum()), 2) == 61351.01
    assert sales_fact["order_id"].nunique() == 200
    assert round(float(sales_fact.groupby("order_id")["line_revenue_eur"].sum().mean()), 2) == 306.76


def test_feature_tables_are_created():
    tables = load_tables(DATA_DIR)
    sales_fact = build_sales_fact(tables)
    daily_features = build_daily_revenue_features(sales_fact)
    customer_features = build_customer_features(sales_fact)

    assert not daily_features.empty
    assert "revenue_lag_7" in daily_features.columns
    assert not customer_features.empty
    assert "recency_days" in customer_features.columns
