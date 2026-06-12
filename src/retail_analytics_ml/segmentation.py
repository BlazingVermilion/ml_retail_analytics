from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

SEGMENT_FEATURES = [
    "recency_days",
    "frequency",
    "monetary_eur",
    "avg_order_value_eur",
    "total_quantity",
    "unique_products",
    "unique_categories",
    "profit_margin",
]


def train_customer_segmentation(
    customer_features: pd.DataFrame,
    output_dir: str | Path,
    n_clusters: int = 4,
    random_state: int = 42,
) -> dict[str, Path]:
    """Cluster customers using RFM and behavioral features."""
    output_path = Path(output_dir)
    model_path = output_path / "models"
    reports_path = output_path / "reports"
    for directory in (model_path, reports_path):
        directory.mkdir(parents=True, exist_ok=True)

    df = customer_features.copy()
    n_clusters = min(n_clusters, max(2, len(df) - 1))
    X = df[SEGMENT_FEATURES].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=n_clusters, n_init=20, random_state=random_state)
    clusters = model.fit_predict(X_scaled)
    df["cluster_id"] = clusters

    segment_names = _name_segments(df)
    df["segment_name"] = df["cluster_id"].map(segment_names)

    summary = (
        df.groupby(["cluster_id", "segment_name"])
        .agg(
            customer_count=("customer_id", "nunique"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            total_revenue_eur=("monetary_eur", "sum"),
            avg_customer_revenue_eur=("monetary_eur", "mean"),
            avg_order_value_eur=("avg_order_value_eur", "mean"),
            avg_profit_margin=("profit_margin", "mean"),
        )
        .reset_index()
        .sort_values("total_revenue_eur", ascending=False)
    )

    metrics = {
        "model": "KMeans",
        "n_clusters": int(n_clusters),
        "customer_rows": int(len(df)),
        "features": SEGMENT_FEATURES,
        "silhouette_score": float(silhouette_score(X_scaled, clusters)) if len(set(clusters)) > 1 else 0.0,
        "note": "Unsupervised segmentation for business interpretation; segment names are assigned from cluster-level RFM behavior.",
    }

    segmented_file = reports_path / "customer_segments.csv"
    summary_file = reports_path / "customer_segment_summary.csv"
    metrics_file = reports_path / "customer_segmentation_metrics.json"
    model_file = model_path / "customer_segmentation_kmeans.joblib"
    scaler_file = model_path / "customer_segmentation_scaler.joblib"

    df.to_csv(segmented_file, index=False)
    summary.to_csv(summary_file, index=False)
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    joblib.dump(model, model_file)
    joblib.dump(scaler, scaler_file)

    return {
        "segments": segmented_file,
        "summary": summary_file,
        "metrics": metrics_file,
        "model": model_file,
        "scaler": scaler_file,
    }


def _name_segments(df: pd.DataFrame) -> dict[int, str]:
    """Assign business-friendly labels to unsupervised clusters.

    Labels are based on a simple RFM composite score: higher monetary value and
    frequency are better, while lower recency means the customer purchased more
    recently. This keeps the model unsupervised while making the output easier
    for a BI user to interpret.
    """
    cluster_stats = (
        df.groupby("cluster_id")
        .agg(
            monetary_eur=("monetary_eur", "mean"),
            frequency=("frequency", "mean"),
            recency_days=("recency_days", "mean"),
        )
        .reset_index()
    )

    for col in ["monetary_eur", "frequency", "recency_days"]:
        std = cluster_stats[col].std(ddof=0) or 1.0
        cluster_stats[f"{col}_z"] = (cluster_stats[col] - cluster_stats[col].mean()) / std

    cluster_stats["rfm_score"] = (
        cluster_stats["monetary_eur_z"]
        + cluster_stats["frequency_z"]
        - cluster_stats["recency_days_z"]
    )
    ranked_clusters = cluster_stats.sort_values("rfm_score", ascending=False)["cluster_id"].astype(int).tolist()
    label_order = [
        "High-Value Loyal Customers",
        "Recent Frequent Buyers",
        "Mid-Market Shoppers",
        "Low-Value Occasional Buyers",
    ]
    return {cluster_id: label_order[i] for i, cluster_id in enumerate(ranked_clusters)}
