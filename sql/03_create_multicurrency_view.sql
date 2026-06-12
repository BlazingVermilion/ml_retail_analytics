-- Business-ready analytical view used by Power BI.
-- The source order item unit_price is treated as EUR.

SET search_path TO retail;

CREATE OR REPLACE VIEW vw_sales_multicurrency AS
WITH rate_pivot AS (
    SELECT
        rate_date,
        MAX(CASE WHEN target_currency = 'USD' THEN rate END) AS rate_usd,
        MAX(CASE WHEN target_currency = 'GBP' THEN rate END) AS rate_gbp,
        MAX(CASE WHEN target_currency = 'INR' THEN rate END) AS rate_inr
    FROM exchange_rates
    WHERE base_currency = 'EUR'
    GROUP BY rate_date
)
SELECT
    o.order_id,
    o.order_date,
    o.status,
    c.customer_id,
    c.country,
    c.city,
    p.product_id,
    p.product_name,
    cat.category_id,
    cat.category_name,
    oi.quantity,
    oi.unit_price AS unit_price_eur,
    oi.quantity * oi.unit_price AS revenue_eur,
    oi.quantity * p.cost_price AS cost_eur,
    (oi.quantity * oi.unit_price) - (oi.quantity * p.cost_price) AS profit_eur,
    rp.rate_usd,
    rp.rate_gbp,
    rp.rate_inr,
    (oi.quantity * oi.unit_price) * rp.rate_usd AS revenue_usd,
    (oi.quantity * oi.unit_price) * rp.rate_gbp AS revenue_gbp,
    (oi.quantity * oi.unit_price) * rp.rate_inr AS revenue_inr
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN rate_pivot rp ON o.order_date = rp.rate_date;
