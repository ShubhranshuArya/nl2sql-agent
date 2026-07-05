# ER Diagram — Global E-Commerce & Supply Chain Database

Entity-relationship diagram for the 8 interconnected tables. Crow's-foot notation
(`||` = exactly one, `o{` = zero-or-many). Primary keys are marked `PK`, foreign
keys `FK`.

```mermaid
erDiagram
    CUSTOMERS ||--o{ TRANSACTIONS : "places"
    PRODUCTS  ||--o{ TRANSACTIONS : "sold_in"
    CUSTOMERS ||--o{ RETURNS      : "requests"
    PRODUCTS  ||--o{ RETURNS      : "returned_as"
    TRANSACTIONS ||--o{ RETURNS   : "may_be_returned"
    PRODUCTS  ||--|| INVENTORY     : "stocked_as"
    PRODUCTS  ||--o{ PRICE_HISTORY : "priced_over_time"
    PRODUCTS  ||--o{ SUPPLIER_COSTS: "sourced_from"

    CUSTOMERS {
        string  customer_id PK
        string  first_name
        string  last_name
        string  country
        string  currency
        int     age
        string  gender
        date    registration_date
        bool    is_premium
        bool    email_verified
        string  email
    }

    PRODUCTS {
        string  product_id PK
        string  name
        string  category
        string  brand
        float   unit_price_usd
        float   unit_cost_usd
        float   weight_kg
        bool    is_active
        date    launch_date
    }

    TRANSACTIONS {
        string  transaction_id PK
        string  customer_id FK
        string  product_id FK
        date    date
        int     quantity
        float   unit_price_usd
        float   discount_pct
        float   revenue_usd
        float   cost_usd
        float   profit_usd
        float   shipping_cost_usd
        string  channel
        string  payment_method
        string  status
        string  country
        string  category
    }

    RETURNS {
        string  return_id PK
        string  transaction_id FK
        string  customer_id FK
        string  product_id FK
        date    return_date
        string  reason
        float   refund_amount_usd
        bool    restocked
    }

    INVENTORY {
        string  product_id PK "FK -> PRODUCTS"
        string  category
        int     stock_units
        int     reorder_point
        string  warehouse_location
        date    last_restock_date
        int     supplier_lead_days
    }

    PRICE_HISTORY {
        string  product_id PK "FK -> PRODUCTS"
        string  year_month PK
        string  category
        float   listed_price_usd
        float   base_price_usd
        float   competitor_price_usd
        float   price_index
        bool    is_promotional
        float   price_elasticity
        int     units_sold
        float   revenue_usd
        float   margin_pct
    }

    SUPPLIER_COSTS {
        string  product_id PK "FK -> PRODUCTS"
        string  supplier_name PK
        string  category
        int     supplier_rank
        float   unit_cost_usd
        float   ordering_cost_usd
        float   annual_holding_cost_usd
        float   holding_cost_pct
        int     lead_time_days
        int     min_order_qty
        float   reliability_score
        bool    is_primary
    }

    MARKETING_SPEND {
        string  year_month PK
        string  channel PK
        float   spend_usd
        int     impressions
        int     clicks
        float   ctr
        int     actual_orders
        int     actual_customers
        float   actual_revenue_usd
        float   roas
        float   cac_usd
        float   cost_per_order_usd
        float   month_multiplier
    }
```

> Note: `MARKETING_SPEND` has no hard foreign key. It relates to `TRANSACTIONS`
> softly via the shared `channel` value (and to `PRICE_HISTORY`/time-based tables
> via `year_month`), so it is shown standalone.
