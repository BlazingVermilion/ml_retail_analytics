-- Example local CSV loading script for psql.
-- Run from the repository root after creating the tables.
-- Adjust paths if your working directory is different.

SET search_path TO retail;

\copy categories FROM 'data/raw/categories.csv' WITH (FORMAT csv, HEADER true);
\copy customers FROM 'data/raw/customers.csv' WITH (FORMAT csv, HEADER true);
\copy products FROM 'data/raw/products.csv' WITH (FORMAT csv, HEADER true);
\copy orders FROM 'data/raw/orders.csv' WITH (FORMAT csv, HEADER true);
\copy order_items FROM 'data/raw/order_items.csv' WITH (FORMAT csv, HEADER true);
\copy exchange_rates FROM 'data/raw/exchange_rates.csv' WITH (FORMAT csv, HEADER true);
