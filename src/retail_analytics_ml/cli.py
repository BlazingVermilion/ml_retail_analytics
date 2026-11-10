from __future__ import annotations

import argparse
from pathlib import Path

from retail_analytics_ml.data_loader import load_tables
from retail_analytics_ml.feature_engineering import (
    build_customer_features,
    build_daily_revenue_features,
    build_sales_fact,
)
from retail_analytics_ml.forecasting import train_sales_forecast_model
from retail_analytics_ml.reporting import create_all_figures, create_summary_report
from retail_analytics_ml.segmentation import train_customer_segmentation


def run_all(data_dir: str | Path, output_dir: str | Path, forecast_horizon: int = 30) -> None:
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    processed_path = output_path / "processed"
    reports_path = output_path / "reports"
    processed_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    tables = load_tables(data_path)
    sales_fact = build_sales_fact(tables)
    daily_features = build_daily_revenue_features(sales_fact)
    customer_features = build_customer_features(sales_fact)

    sales_fact_path = processed_path / "sales_fact_multicurrency.csv"
    daily_features_path = processed_path / "daily_revenue_features.csv"
    customer_features_path = processed_path / "customer_features_rfm.csv"
    sales_fact.to_csv(sales_fact_path, index=False)
    daily_features.to_csv(daily_features_path, index=False)
    customer_features.to_csv(customer_features_path, index=False)

    forecast_outputs = train_sales_forecast_model(
        daily_features, output_path, forecast_horizon=forecast_horizon
    )
    segment_outputs = train_customer_segmentation(customer_features, output_path)
    create_summary_report(sales_fact, output_path)

    outputs_for_figures = {**forecast_outputs, **segment_outputs}
    figures = create_all_figures(outputs_for_figures, output_path)

    print("Pipeline completed successfully.")
    print(f"Processed datasets: {processed_path}")
    print(f"Reports: {reports_path}")
    print(f"Figures: {output_path / 'figures'}")
    for name, path in figures.items():
        print(f"- {name}: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retail analytics and ML pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-all", help="Run data preparation, forecasting, segmentation, and plots"
    )
    run_parser.add_argument(
        "--data-dir", default="data/raw", help="Directory containing raw CSV files"
    )
    run_parser.add_argument(
        "--output-dir", default="outputs/demo", help="Directory for generated artifacts"
    )
    run_parser.add_argument(
        "--forecast-horizon", type=int, default=30, help="Number of days to forecast"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "run-all":
        run_all(args.data_dir, args.output_dir, forecast_horizon=args.forecast_horizon)


if __name__ == "__main__":
    main()
