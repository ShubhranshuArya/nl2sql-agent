"""Deterministic scorers for evaluating generated SQL.

All functions here are pure / side-effect-free aside from read-only database
execution, so scores are fully reproducible and safe to run in CI. The anchor
metric is execution accuracy: rather than comparing SQL text (many correct
queries differ textually), we execute both the candidate and the reference and
compare their result sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.tools.sql import execute_read_query
from app.tools.validator import validate_sql_safety

_FLOAT_TOL = 1e-6


def _norm_value(v: Any) -> Any:
    """Normalize a single cell for comparison (round floats, leave rest as-is)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        return round(v, 6)
    return v


def _row_tuple(row: Dict[str, Any]) -> Tuple[Any, ...]:
    """Convert a row dict to a value tuple, ignoring column names/aliases.

    Column labels are intentionally dropped: a correct query may alias columns
    differently from the reference, but the underlying values should match.
    """
    return tuple(_norm_value(v) for v in row.values())


def _normalize_rows(rows: List[Dict[str, Any]], order_sensitive: bool) -> List[Tuple[Any, ...]]:
    tuples = [_row_tuple(r) for r in rows]
    if order_sensitive:
        return tuples
    # Order-insensitive: compare as a multiset via a sorted, stringified key so
    # heterogeneous / None values remain comparable across Python versions.
    return sorted(tuples, key=lambda t: tuple(str(x) for x in t))


@dataclass
class CaseScore:
    """Deterministic scores for a single generated-SQL evaluation case."""

    case_id: str
    category: str
    is_safe: bool
    executed: bool
    execution_match: bool
    exact_result_match: bool
    row_count_match: bool
    col_count_match: bool
    safety_error: str = ""
    execution_error: str = ""
    candidate_row_count: Optional[int] = None
    golden_row_count: Optional[int] = None
    notes: List[str] = field(default_factory=list)


def safe_execute(sql: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Execute a query read-only, returning (ok, rows, error_message)."""
    try:
        return True, execute_read_query(sql), ""
    except Exception as e:  # noqa: BLE001 - any failure means non-executable
        return False, [], str(e)


def execution_match(
    candidate_sql: str,
    golden_sql: str,
    order_sensitive: bool = False,
) -> Tuple[bool, List[str]]:
    """True when candidate and golden produce equivalent result sets.

    Returns (matched, notes) where notes explain a mismatch for debugging.
    """
    notes: List[str] = []
    cand_ok, cand_rows, cand_err = safe_execute(candidate_sql)
    if not cand_ok:
        return False, [f"candidate failed to execute: {cand_err}"]
    gold_ok, gold_rows, gold_err = safe_execute(golden_sql)
    if not gold_ok:
        return False, [f"golden failed to execute: {gold_err}"]

    if len(cand_rows) != len(gold_rows):
        notes.append(f"row count differs: candidate={len(cand_rows)} golden={len(gold_rows)}")

    matched = _normalize_rows(cand_rows, order_sensitive) == _normalize_rows(gold_rows, order_sensitive)
    if not matched and not notes:
        notes.append("row values differ")
    return matched, notes


def score_case(
    case_id: str,
    category: str,
    candidate_sql: str,
    golden_sql: str,
    order_sensitive: bool = False,
) -> CaseScore:
    """Compute all deterministic metrics for one generated SQL statement."""
    is_safe, safety_msg = validate_sql_safety(candidate_sql)

    cand_ok, cand_rows, cand_err = (False, [], "")
    if is_safe:
        cand_ok, cand_rows, cand_err = safe_execute(candidate_sql)

    gold_ok, gold_rows, _ = safe_execute(golden_sql)

    match = False
    notes: List[str] = []
    exact = False
    row_match = False
    col_match = False

    if not is_safe:
        notes.append(f"failed safety validation: {safety_msg}")
    elif not cand_ok:
        notes.append(f"failed to execute: {cand_err}")
    elif gold_ok:
        norm_cand = _normalize_rows(cand_rows, order_sensitive)
        norm_gold = _normalize_rows(gold_rows, order_sensitive)
        match = norm_cand == norm_gold
        # Exact match keeps ordering regardless of the order_sensitive flag.
        exact = _normalize_rows(cand_rows, True) == _normalize_rows(gold_rows, True)
        row_match = len(cand_rows) == len(gold_rows)
        col_match = (
            (len(cand_rows[0]) if cand_rows else 0)
            == (len(gold_rows[0]) if gold_rows else 0)
        )
        if not match:
            notes.append("result set differs from golden")

    return CaseScore(
        case_id=case_id,
        category=category,
        is_safe=is_safe,
        executed=cand_ok,
        execution_match=match,
        exact_result_match=exact,
        row_count_match=row_match,
        col_count_match=col_match,
        safety_error="" if is_safe else safety_msg,
        execution_error=cand_err,
        candidate_row_count=len(cand_rows) if cand_ok else None,
        golden_row_count=len(gold_rows) if gold_ok else None,
        notes=notes,
    )


def aggregate(scores: List[CaseScore]) -> Dict[str, Any]:
    """Roll up per-case scores into overall + per-category rates."""
    n = len(scores)

    def rate(pred) -> float:
        return round(sum(1 for s in scores if pred(s)) / n, 4) if n else 0.0

    overall = {
        "n_cases": n,
        "execution_accuracy": rate(lambda s: s.execution_match),
        "safety_rate": rate(lambda s: s.is_safe),
        "executability_rate": rate(lambda s: s.executed),
        "exact_result_match_rate": rate(lambda s: s.exact_result_match),
    }

    by_category: Dict[str, Dict[str, Any]] = {}
    categories = sorted({s.category for s in scores})
    for cat in categories:
        subset = [s for s in scores if s.category == cat]
        m = len(subset)
        by_category[cat] = {
            "n_cases": m,
            "execution_accuracy": round(sum(1 for s in subset if s.execution_match) / m, 4),
            "safety_rate": round(sum(1 for s in subset if s.is_safe) / m, 4),
            "executability_rate": round(sum(1 for s in subset if s.executed) / m, 4),
        }

    return {"overall": overall, "by_category": by_category}
