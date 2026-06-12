from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def create_summary_report(sales_fact: pd.DataFrame, output_dir: str | Path) -> Path:
    output_path = Path(output_dir) / "reports"
    output_path.mkdir(parents=True, exist_ok=True)

    summary = {
        "orders": int(sales_fact["order_id"].nunique()),
        "customers": int(sales_fact["customer_id"].nunique()),
        "products": int(sales_fact["product_id"].nunique()),
        "categories": int(sales_fact["category_id"].nunique()),
        "date_min": str(sales_fact["order_date"].min().date()),
        "date_max": str(sales_fact["order_date"].max().date()),
        "total_revenue_eur": round(float(sales_fact["line_revenue_eur"].sum()), 2),
        "total_profit_eur": round(float(sales_fact["line_profit_eur"].sum()), 2),
        "average_order_value_eur": round(
            float(sales_fact.groupby("order_id")["line_revenue_eur"].sum().mean()), 2
        ),
        "top_category_by_revenue": str(
            sales_fact.groupby("category_name")["line_revenue_eur"].sum().idxmax()
        ),
        "top_country_by_revenue": str(sales_fact.groupby("country")["line_revenue_eur"].sum().idxmax()),
    }
    path = output_path / "business_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def plot_forecast(forecast_csv: str | Path, output_dir: str | Path) -> Path:
    forecast = pd.read_csv(forecast_csv, parse_dates=["order_date"])
    figures_path = Path(output_dir) / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)

    historical = forecast[forecast["row_type"] == "historical"].copy()
    future = forecast[forecast["row_type"] == "future_forecast"].copy()

    plt.figure(figsize=(12, 6))
    plt.plot(historical["order_date"], historical["revenue_eur"], label="Actual daily revenue")
    plt.plot(historical["order_date"], historical["predicted_revenue_eur"], label="Model prediction")
    plt.plot(future["order_date"], future["predicted_revenue_eur"], linestyle="--", label="30-day forecast")
    plt.title("Sales Forecasting: Actual vs Predicted Revenue")
    plt.xlabel("Date")
    plt.ylabel("Revenue (EUR)")
    plt.legend()
    plt.tight_layout()
    path = figures_path / "sales_forecast_actual_vs_predicted.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def plot_feature_importance(feature_importance_csv: str | Path, output_dir: str | Path, top_n: int = 10) -> Path:
    importance = pd.read_csv(feature_importance_csv).head(top_n).sort_values("importance")
    figures_path = Path(output_dir) / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.barh(importance["feature"], importance["importance"])
    plt.title("Top Forecasting Features")
    plt.xlabel("Random Forest Feature Importance")
    plt.tight_layout()
    path = figures_path / "sales_forecast_feature_importance.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def plot_customer_segments(segments_csv: str | Path, output_dir: str | Path) -> Path:
    segments = pd.read_csv(segments_csv)
    figures_path = Path(output_dir) / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    for segment_name, group in segments.groupby("segment_name"):
        plt.scatter(group["recency_days"], group["monetary_eur"], label=segment_name, s=80)
    plt.title("Customer Segmentation: Recency vs Monetary Value")
    plt.xlabel("Recency (days since last order)")
    plt.ylabel("Customer revenue (EUR)")
    plt.legend(fontsize=8)
    plt.tight_layout()
    path = figures_path / "customer_segments_recency_monetary.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def plot_segment_revenue(segment_summary_csv: str | Path, output_dir: str | Path) -> Path:
    summary = pd.read_csv(segment_summary_csv).sort_values("total_revenue_eur")
    figures_path = Path(output_dir) / "figures"
    figures_path.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.barh(summary["segment_name"], summary["total_revenue_eur"])
    plt.title("Total Revenue by Customer Segment")
    plt.xlabel("Total Revenue (EUR)")
    plt.tight_layout()
    path = figures_path / "customer_segment_revenue.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def create_all_figures(outputs: dict[str, Path], output_dir: str | Path) -> dict[str, Path]:
    return {
        "forecast_plot": plot_forecast(outputs["forecast"], output_dir),
        "feature_importance_plot": plot_feature_importance(outputs["feature_importance"], output_dir),
        "customer_segments_plot": plot_customer_segments(outputs["segments"], output_dir),
        "segment_revenue_plot": plot_segment_revenue(outputs["summary"], output_dir),
    }
