"""Pytest gate for the SQL generator evaluation.

Only deterministic metrics gate CI. The optional RAGAS score is reported by the
runner but never asserted here.

Tests are split so the fast, offline checks (dataset integrity, metric logic)
always run, while the end-to-end threshold test - which invokes the LLM via the
SQL generator node - is skipped automatically when no LLM_API_KEY is configured.

Run:
    uv run pytest backend/evals/test_evals.py -v
"""
from __future__ import annotations

import asyncio
import os

import pytest

from app.evaluation.dataset import load_cases, validate_dataset
from app.evaluation.metrics import aggregate, score_case

# Deterministic gates. Execution-accuracy threshold is overridable for tuning.
EXEC_ACCURACY_THRESHOLD = float(os.getenv("EVAL_EXEC_THRESHOLD", "0.8"))
SAFETY_RATE_THRESHOLD = 1.0

_needs_llm = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="LLM_API_KEY not set; skipping end-to-end SQL generation eval.",
)


# --- Offline checks (no LLM) ------------------------------------------------


def test_golden_dataset_is_valid():
    """Every golden_sql must be safe and execute against the built database."""
    cases = load_cases()
    assert len(cases) == 15, "expected 15 seed cases"
    result = validate_dataset(cases)
    assert result.ok, "golden dataset invalid:\n" + "\n".join(result.errors)


def test_execution_match_identical_query():
    """Semantically identical queries (different alias) score as a match."""
    s = score_case(
        "unit_match",
        "unit",
        candidate_sql="SELECT SUM(revenue_usd) AS r FROM transactions",
        golden_sql="SELECT SUM(revenue_usd) AS total FROM transactions",
    )
    assert s.execution_match and s.is_safe and s.executed


def test_unsafe_query_is_flagged():
    """A destructive statement fails safety and never counts as a match."""
    s = score_case(
        "unit_unsafe",
        "unit",
        candidate_sql="DROP TABLE transactions",
        golden_sql="SELECT 1",
    )
    assert not s.is_safe and not s.execution_match


def test_wrong_result_is_not_a_match():
    s = score_case(
        "unit_wrong",
        "unit",
        candidate_sql="SELECT COUNT(*) FROM transactions WHERE status = 'cancelled'",
        golden_sql="SELECT COUNT(*) FROM transactions",
    )
    assert not s.execution_match


# --- End-to-end threshold gate (requires LLM) -------------------------------


@pytest.fixture(scope="module")
def eval_results():
    from app.evaluation.runner import run_all

    return asyncio.run(run_all(self_correct=False))


@_needs_llm
def test_execution_accuracy_meets_threshold(eval_results):
    agg = aggregate([r.score for r in eval_results])["overall"]
    assert agg["execution_accuracy"] >= EXEC_ACCURACY_THRESHOLD, (
        f"execution accuracy {agg['execution_accuracy']:.2%} "
        f"below threshold {EXEC_ACCURACY_THRESHOLD:.2%}"
    )


@_needs_llm
def test_all_generated_sql_is_safe(eval_results):
    agg = aggregate([r.score for r in eval_results])["overall"]
    assert agg["safety_rate"] >= SAFETY_RATE_THRESHOLD, (
        f"safety rate {agg['safety_rate']:.2%} below required "
        f"{SAFETY_RATE_THRESHOLD:.2%}"
    )
