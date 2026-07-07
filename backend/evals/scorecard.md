# SQL Generator Evaluation Scorecard

Mode: `single_shot`  |  Cases: 15

## Overall (deterministic)

| Metric | Value |
| --- | --- |
| Execution accuracy | 86.67% |
| Safety rate | 100.00% |
| Executability rate | 93.33% |
| Exact result match | 73.33% |

## By category

| Category | Cases | Exec accuracy | Safety | Executable |
| --- | --- | --- | --- | --- |
| boolean_flag_filter | 1 | 100.00% | 100.00% | 100.00% |
| computed_ratio_join | 1 | 0.00% | 100.00% | 0.00% |
| cte_subquery | 1 | 100.00% | 100.00% | 100.00% |
| date_filter | 1 | 100.00% | 100.00% | 100.00% |
| distinct_count | 1 | 100.00% | 100.00% | 100.00% |
| enum_categorical | 1 | 100.00% | 100.00% | 100.00% |
| group_by_aggregate | 1 | 100.00% | 100.00% | 100.00% |
| having_clause | 1 | 100.00% | 100.00% | 100.00% |
| monthly_time_series | 1 | 100.00% | 100.00% | 100.00% |
| multi_condition_where | 1 | 100.00% | 100.00% | 100.00% |
| single_table_aggregate | 1 | 100.00% | 100.00% | 100.00% |
| single_table_filter | 1 | 100.00% | 100.00% | 100.00% |
| three_table_join | 1 | 100.00% | 100.00% | 100.00% |
| top_n_order_limit | 1 | 0.00% | 100.00% | 100.00% |
| two_table_join | 1 | 100.00% | 100.00% | 100.00% |

## Per-case

| ID | Category | Match | Safe | Exec | Attempts | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| sql01_single_filter | single_table_filter | yes | yes | yes | 1 |  |
| sql02_single_aggregate | single_table_aggregate | yes | yes | yes | 1 |  |
| sql03_group_by | group_by_aggregate | yes | yes | yes | 1 |  |
| sql04_top_n | top_n_order_limit | no | yes | yes | 1 | result set differs from golden |
| sql05_two_table_join | two_table_join | yes | yes | yes | 1 |  |
| sql06_three_table_join | three_table_join | yes | yes | yes | 1 |  |
| sql07_date_filter | date_filter | yes | yes | yes | 1 |  |
| sql08_time_series | monthly_time_series | yes | yes | yes | 1 |  |
| sql09_distinct_count | distinct_count | yes | yes | yes | 1 |  |
| sql10_multi_condition | multi_condition_where | yes | yes | yes | 1 |  |
| sql11_cte_subquery | cte_subquery | yes | yes | yes | 1 |  |
| sql12_having | having_clause | yes | yes | yes | 1 |  |
| sql13_boolean_flag | boolean_flag_filter | yes | yes | yes | 1 |  |
| sql14_enum_filter | enum_categorical | yes | yes | yes | 1 |  |
| sql15_computed_ratio | computed_ratio_join | no | yes | no | 1 | failed to execute: Query execution failed: circular reference: returns |
