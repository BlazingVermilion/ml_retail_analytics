# ML Design

This project extends a traditional SQL + Power BI retail analytics dashboard with two machine-learning components. The goal is to demonstrate a professional analytics workflow: feature engineering, model training, reproducible artifacts, evaluation metrics, and BI-ready ML outputs.

The dataset is small, so the models should be interpreted as portfolio-grade analytical extensions rather than production-grade forecasting or segmentation services.

## 1. Sales Forecasting

**Task:** Estimate daily revenue and generate a 30-day forward revenue forecast.

**Model:** `RandomForestRegressor` from scikit-learn.

**Why this model:**

- Works well with tabular retail features.
- Captures non-linear relationships between demand activity, calendar effects, and revenue.
- Produces feature importance for business interpretation.
- Can be trained and reproduced locally without cloud services.

**Feature groups:**

- Calendar features: day of week, month, quarter, day of month, weekend flag.
- Demand/activity features: order count, item quantity, unique customers, unique products.
- Time-series features: revenue lags and rolling revenue/order means.

The historical fit uses observed same-day activity. The forward backtest instead steps through the held-out days in forecast-horizon blocks. At each origin the model sees only preceding observations, estimates unknown activity from prior days and rolls its own predicted revenue forward. The comparison holds the preceding seven-day mean fixed throughout the same window.

**Outputs:**

- `outputs/demo/reports/sales_forecast.csv`
- `outputs/demo/reports/sales_forecast_metrics.json`
- `outputs/demo/reports/sales_forecast_feature_importance.csv`
- `outputs/demo/models/sales_forecast_random_forest.joblib`
- `outputs/demo/figures/sales_forecast_actual_vs_predicted.png`
- `outputs/demo/figures/sales_forecast_feature_importance.png`

## 2. Customer Segmentation

**Task:** Group customers by purchasing behavior for business targeting and customer analysis.

**Model:** `KMeans` clustering with standardized RFM and behavioral features.

**Feature groups:**

- RFM: recency, frequency, monetary value.
- Basket behavior: total quantity, average order value, unique products, unique categories.
- Profitability: gross profit and profit margin.

**Segment labels:** Clusters are generated without labels, then mapped to business-friendly names using cluster-level RFM behavior:

- High-Value Loyal Customers
- Recent Frequent Buyers
- Mid-Market Shoppers
- Low-Value Occasional Buyers

**Outputs:**

- `outputs/demo/reports/customer_segments.csv`
- `outputs/demo/reports/customer_segment_summary.csv`
- `outputs/demo/reports/customer_segmentation_metrics.json`
- `outputs/demo/models/customer_segmentation_kmeans.joblib`
- `outputs/demo/models/customer_segmentation_scaler.joblib`
- `outputs/demo/figures/customer_segments_recency_monetary.png`
- `outputs/demo/figures/customer_segment_revenue.png`

## Power BI Integration

The generated ML outputs can be imported into Power BI as additional tables:

- Use `sales_forecast.csv` for an **Actual vs Forecast Revenue** page.
- Use `customer_segments.csv` and `customer_segment_summary.csv` for a **Customer Segmentation** page.

This upgrades the dashboard from descriptive BI to predictive and segment-based analytics.
