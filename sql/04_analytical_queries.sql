-- Useful analytical SQL queries for validating and exploring the project.

SET search_path TO retail;

-- KPI validation: total revenue, order count, and average order value.
SELECT
    ROUND(SUM(revenue_eur), 2) AS total_revenue_eur,
    COUNT(DISTINCT order_id) AS order_count,
    ROUND(SUM(revenue_eur) / COUNT(DISTINCT order_id), 2) AS avg_order_value_eur
FROM vw_sales_multicurrency;

-- Revenue by category.
SELECT
    category_name,
    ROUND(SUM(revenue_eur), 2) AS revenue_eur
FROM vw_sales_multicurrency
GROUP BY category_name
ORDER BY revenue_eur DESC;

-- Revenue by country.
SELECT
    country,
    ROUND(SUM(revenue_eur), 2) AS revenue_eur,
    COUNT(DISTINCT order_id) AS orders
FROM vw_sales_multicurrency
GROUP BY country
ORDER BY revenue_eur DESC;

-- Daily sales trend.
SELECT
    order_date,
    ROUND(SUM(revenue_eur), 2) AS daily_revenue_eur,
    COUNT(DISTINCT order_id) AS daily_orders
FROM vw_sales_multicurrency
GROUP BY order_date
ORDER BY order_date;

-- Customer RFM base for segmentation.
SELECT
    customer_id,
    country,
    MAX(order_date) AS last_order_date,
    COUNT(DISTINCT order_id) AS frequency,
    ROUND(SUM(revenue_eur), 2) AS monetary_eur,
    ROUND(SUM(revenue_eur) / COUNT(DISTINCT order_id), 2) AS avg_order_value_eur
FROM vw_sales_multicurrency
GROUP BY customer_id, country
ORDER BY monetary_eur DESC;
