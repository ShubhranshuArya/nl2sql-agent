# Data Card — Global E-Commerce & Supply Chain Database

Minimal schema reference for LLM-driven SQL generation. 8 CSV tables in `data/`.
All monetary values are USD. Dates are `YYYY-MM-DD`; monthly periods are `YYYY-MM`.

## Relationships (join keys)

| From | Column | To | Column | Cardinality |
|------|--------|----|--------|-------------|
| transactions | customer_id | customers | customer_id | many-to-one |
| transactions | product_id | products | product_id | many-to-one |
| returns | transaction_id | transactions | transaction_id | one-to-one* |
| returns | customer_id | customers | customer_id | many-to-one |
| returns | product_id | products | product_id | many-to-one |
| inventory | product_id | products | product_id | one-to-one |
| price_history | product_id | products | product_id | many-to-one |
| supplier_costs | product_id | products | product_id | many-to-one |
| marketing_spend | channel | transactions | channel | soft (no FK) |

\* Each return references one transaction; only a subset of transactions have returns.

**Hubs:** `products` (product_id) and `customers` (customer_id) are the central entities.

---

## Tables

### customers (~8,000 rows) — PK: `customer_id`
Registered customer accounts and demographics.

| Column | Type | Description |
|--------|------|-------------|
| customer_id | str | Unique customer ID (e.g. CUST00001) |
| first_name | str | First name |
| last_name | str | Last name |
| country | str | Country of residence |
| currency | str | Preferred currency code (GBP, USD, EUR, …) |
| age | int | Age in years |
| gender | str | M / F / Other |
| registration_date | date | Sign-up date |
| is_premium | bool | Premium membership flag |
| email_verified | bool | Whether email is verified |
| email | str | Email address |

### products (~500 rows) — PK: `product_id`
Master catalog of sellable products.

| Column | Type | Description |
|--------|------|-------------|
| product_id | str | Unique product ID (e.g. PROD0001) |
| name | str | Product display name |
| category | str | Product category (Books, Clothing, Electronics, …) |
| brand | str | Brand name |
| unit_price_usd | float | Current list selling price |
| unit_cost_usd | float | Current unit cost |
| weight_kg | float | Weight in kilograms |
| is_active | bool | Whether currently sold |
| launch_date | date | First availability date |

### transactions (~100,000 rows) — PK: `transaction_id`
Line-item sales orders. Central fact table. FK → customers, products.

| Column | Type | Description |
|--------|------|-------------|
| transaction_id | str | Unique transaction ID (e.g. TXN000001) |
| customer_id | str | FK → customers |
| product_id | str | FK → products |
| date | date | Order date |
| quantity | int | Units purchased |
| unit_price_usd | float | Price per unit at sale time |
| discount_pct | float | Discount fraction (0–1) |
| revenue_usd | float | Net revenue (after discount) |
| cost_usd | float | Total cost of goods |
| profit_usd | float | revenue − cost |
| shipping_cost_usd | float | Shipping cost |
| channel | str | Acquisition channel (organic_search, paid_search, social_media, email, direct, referral) |
| payment_method | str | credit_card, paypal, bank_transfer, debit_card, … |
| status | str | Order status (completed, …) |
| country | str | Destination country |
| category | str | Product category (denormalized from products) |

### returns (~7,100 rows) — PK: `return_id`
Product returns tied to a transaction. FK → transactions, customers, products.

| Column | Type | Description |
|--------|------|-------------|
| return_id | str | Unique return ID (e.g. RET00001) |
| transaction_id | str | FK → transactions |
| customer_id | str | FK → customers |
| product_id | str | FK → products |
| return_date | date | Date of return |
| reason | str | not_as_described, wrong_item, defective, late_delivery, changed_mind |
| refund_amount_usd | float | Amount refunded |
| restocked | bool | Whether item was restocked |

### inventory (~500 rows) — PK: `product_id` (FK → products)
Current warehouse stock, one row per product.

| Column | Type | Description |
|--------|------|-------------|
| product_id | str | FK → products (also PK) |
| category | str | Product category |
| stock_units | int | Units currently in stock |
| reorder_point | int | Stock level triggering reorder |
| warehouse_location | str | Warehouse region (US-West, EU-Central, APAC, …) |
| last_restock_date | date | Most recent restock date |
| supplier_lead_days | int | Lead time for replenishment |

### price_history (~18,000 rows) — PK: (`product_id`, `year_month`)
Monthly pricing and sales snapshot per product. FK → products.

| Column | Type | Description |
|--------|------|-------------|
| product_id | str | FK → products |
| category | str | Product category |
| year_month | str | Period (YYYY-MM) |
| listed_price_usd | float | Actual listed price that month |
| base_price_usd | float | Reference/base price |
| competitor_price_usd | float | Competitor's price |
| price_index | float | listed / base price ratio |
| is_promotional | bool | Whether on promotion |
| price_elasticity | float | Demand elasticity estimate |
| units_sold | int | Units sold that month |
| revenue_usd | float | Revenue that month |
| margin_pct | float | Margin fraction |

### supplier_costs (~1,000 rows) — PK: (`product_id`, `supplier_name`)
Supplier sourcing options per product; multiple suppliers ranked. FK → products.

| Column | Type | Description |
|--------|------|-------------|
| product_id | str | FK → products |
| category | str | Product category |
| supplier_name | str | Supplier name (e.g. BookSupply DE) |
| supplier_rank | int | Preference rank (1 = best) |
| unit_cost_usd | float | Cost per unit from this supplier |
| ordering_cost_usd | float | Fixed cost per order |
| annual_holding_cost_usd | float | Annual holding cost |
| holding_cost_pct | float | Holding cost as fraction of value |
| lead_time_days | int | Delivery lead time |
| min_order_qty | int | Minimum order quantity |
| reliability_score | float | Supplier reliability (0–1) |
| is_primary | bool | Whether primary supplier (rank 1) |

### marketing_spend (~216 rows) — PK: (`year_month`, `channel`)
Monthly marketing performance per channel. Soft link to transactions via `channel`.

| Column | Type | Description |
|--------|------|-------------|
| year_month | str | Period (YYYY-MM) |
| channel | str | Marketing channel (matches transactions.channel) |
| spend_usd | float | Ad spend |
| impressions | int | Impressions served |
| clicks | int | Clicks received |
| ctr | float | Click-through rate |
| actual_orders | int | Orders attributed |
| actual_customers | int | Customers attributed |
| actual_revenue_usd | float | Attributed revenue |
| roas | float | Return on ad spend |
| cac_usd | float | Customer acquisition cost |
| cost_per_order_usd | float | Cost per order |
| month_multiplier | float | Seasonal multiplier |

---

## Notes for query generation
- Join sales analysis on `transactions` as the fact table; enrich via `products` and `customers`.
- `category` and `unit_price_usd` are denormalized into several tables; prefer `products`/`transactions` context as the source of truth for a given question.
- Time-series questions: use `price_history.year_month` and `marketing_spend.year_month`.
- `inventory` is per-product (1:1); `supplier_costs` and `price_history` are 1:many per product.
- Database is read-only for the agent; no table has update-in-place semantics.
