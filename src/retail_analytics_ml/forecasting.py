from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

FORECAST_FEATURES = [
    "day_of_week",
    "month",
    "quarter",
    "day_of_month",
    "is_weekend",
    "order_count",
    "item_quantity",
    "unique_customers",
    "unique_products",
    "revenue_lag_1",
    "revenue_lag_7",
    "revenue_lag_14",
    "revenue_lag_30",
    "revenue_rolling_mean_7",
    "revenue_rolling_mean_14",
    "revenue_rolling_mean_30",
    "order_rolling_mean_7",
    "order_rolling_mean_14",
    "order_rolling_mean_30",
]
TARGET = "revenue_eur"


def _mape(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    non_zero = y_true_arr != 0
    if not non_zero.any():
        return 0.0
    return float(np.mean(np.abs((y_true_arr[non_zero] - y_pred_arr[non_zero]) / y_true_arr[non_zero])) * 100)


def train_sales_forecast_model(
    daily_features: pd.DataFrame,
    output_dir: str | Path,
    forecast_horizon: int = 30,
    random_state: int = 42,
) -> dict[str, Path]:
    """Train a RandomForestRegressor and generate historical predictions + future forecast."""
    output_path = Path(output_dir)
    model_path = output_path / "models"
    reports_path = output_path / "reports"
    figures_path = output_path / "figures"
    for directory in (model_path, reports_path, figures_path):
        directory.mkdir(parents=True, exist_ok=True)

    df = daily_features.copy().sort_values("order_date").reset_index(drop=True)
    df["order_date"] = pd.to_datetime(df["order_date"])

    split_idx = max(int(len(df) * 0.8), 1)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(train_df[FORECAST_FEATURES], train_df[TARGET])

    df["predicted_revenue_eur"] = model.predict(df[FORECAST_FEATURES])
    test_pred = df.loc[test_df.index, "predicted_revenue_eur"]

    # Naive baseline: previous seven-day rolling average.
    naive_pred = test_df["revenue_rolling_mean_7"].fillna(train_df[TARGET].mean())
    metrics = {
        "model": "RandomForestRegressor",
        "target": TARGET,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "forecast_horizon_days": int(forecast_horizon),
        "mae": float(mean_absolute_error(test_df[TARGET], test_pred)),
        "rmse": float(np.sqrt(mean_squared_error(test_df[TARGET], test_pred))),
        "mape_percent_nonzero_days": _mape(test_df[TARGET], test_pred),
        "r2": float(r2_score(test_df[TARGET], test_pred)) if len(test_df) > 1 else 0.0,
        "baseline_mae_previous_7d_mean": float(mean_absolute_error(test_df[TARGET], naive_pred)),
        "note": "Small course dataset; model is intended as a portfolio-grade ML extension, not a production forecast service.",
    }

    # Evaluate the actual forward path using only data known at each forecast origin.
    if forecast_horizon > 0:
        predictions = []
        baseline = []
        for origin in range(split_idx, len(df), forecast_horizon):
            observed = df.iloc[:origin]
            days = min(forecast_horizon, len(df) - origin)
            block = _forecast_future(observed, model, days)
            predictions.extend(block["predicted_revenue_eur"])
            baseline.extend([observed[TARGET].tail(7).mean()] * days)
        metrics["forward_backtest"] = {
            "horizon_days": forecast_horizon,
            "test_days": len(predictions),
            "mae_eur": float(mean_absolute_error(test_df[TARGET], predictions)),
            "baseline_mae_eur": float(mean_absolute_error(test_df[TARGET], baseline)),
        }
    metrics["note"] = "Top-level errors use observed same-day activity. Forward backtest errors use only pre-origin observations."

    history = df[["order_date", "revenue_eur", "predicted_revenue_eur"]].copy()
    history["row_type"] = "historical"

    future = _forecast_future(df, model, forecast_horizon)
    forecast = pd.concat([history, future], ignore_index=True)

    feature_importance = pd.DataFrame(
        {
            "feature": FORECAST_FEATURES,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    model_file = model_path / "sales_forecast_random_forest.joblib"
    metrics_file = reports_path / "sales_forecast_metrics.json"
    forecast_file = reports_path / "sales_forecast.csv"
    importance_file = reports_path / "sales_forecast_feature_importance.csv"
    metadata_file = reports_path / "sales_forecast_model_metadata.json"

    joblib.dump(model, model_file)
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    forecast.to_csv(forecast_file, index=False)
    feature_importance.to_csv(importance_file, index=False)
    metadata_file.write_text(
        json.dumps(
            {
                "model_family": "tree_based_regression",
                "algorithm": "RandomForestRegressor",
                "features": FORECAST_FEATURES,
                "target": TARGET,
                "forecast_horizon_days": forecast_horizon,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "model": model_file,
        "metrics": metrics_file,
        "forecast": forecast_file,
        "feature_importance": importance_file,
        "metadata": metadata_file,
    }


def _forecast_future(df: pd.DataFrame, model: RandomForestRegressor, horizon: int) -> pd.DataFrame:
    history_values = df["revenue_eur"].astype(float).tolist()
    last_date = df["order_date"].max()
    historical_means = {
        "order_count": float(df["order_count"].tail(30).mean()),
        "item_quantity": float(df["item_quantity"].tail(30).mean()),
        "unique_customers": float(df["unique_customers"].tail(30).mean()),
        "unique_products": float(df["unique_products"].tail(30).mean()),
    }
    rows: list[dict[str, float | str | pd.Timestamp]] = []

    for step in range(1, horizon + 1):
        date = last_date + pd.Timedelta(days=step)
        candidate = {
            "order_date": date,
            "day_of_week": date.dayofweek,
            "month": date.month,
            "quarter": (date.month - 1) // 3 + 1,
            "day_of_month": date.day,
            "is_weekend": int(date.dayofweek in [5, 6]),
            **historical_means,
            "revenue_lag_1": history_values[-1] if len(history_values) >= 1 else 0.0,
            "revenue_lag_7": history_values[-7] if len(history_values) >= 7 else 0.0,
            "revenue_lag_14": history_values[-14] if len(history_values) >= 14 else 0.0,
            "revenue_lag_30": history_values[-30] if len(history_values) >= 30 else 0.0,
            "revenue_rolling_mean_7": float(np.mean(history_values[-7:])) if len(history_values) >= 7 else 0.0,
            "revenue_rolling_mean_14": float(np.mean(history_values[-14:])) if len(history_values) >= 14 else 0.0,
            "revenue_rolling_mean_30": float(np.mean(history_values[-30:])) if len(history_values) >= 30 else 0.0,
            "order_rolling_mean_7": historical_means["order_count"],
            "order_rolling_mean_14": historical_means["order_count"],
            "order_rolling_mean_30": historical_means["order_count"],
        }
        prediction = float(model.predict(pd.DataFrame([candidate])[FORECAST_FEATURES])[0])
        prediction = max(prediction, 0.0)
        history_values.append(prediction)
        rows.append(
            {
                "order_date": date,
                "revenue_eur": np.nan,
                "predicted_revenue_eur": prediction,
                "row_type": "future_forecast",
            }
        )
    return pd.DataFrame(rows)
