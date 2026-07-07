"""Runs the SQL generator node in isolation over the golden dataset.

The node under test is ``app.agents.sql_generator.sql_generator_node``. Rather
than driving the whole LangGraph, we construct a minimal ``AgentState`` per case
and invoke the node directly, supplying ``selected_tables`` and the query as
fixtures. This isolates SQL-generation quality from upstream router / rewriter /
table_selector behaviour.

Two modes:
- single-shot (default): one generation call, scored as-is.
- self-correction (--self-correct): loops up to the graph's retry budget,
  mirroring the validator/executor edges in app.graph.graph, feeding validation
  or execution errors back to the node. Reports whether it recovers.

Usage:
    uv run python -m app.evaluation.runner [--self-correct] [--output PATH]
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agents.sql_generator import sql_generator_node
from app.evaluation import ragas_eval
from app.evaluation.dataset import GoldenCase, load_cases
from app.evaluation.metrics import CaseScore, safe_execute, score_case
from app.tools.schema import get_database_schema_string
from app.tools.validator import validate_sql_safety

# Matches the graph's retry policy (retry_count < 3 -> regenerate), giving an
# initial attempt plus up to three corrective retries.
_MAX_ATTEMPTS = 4


@dataclass
class CaseResult:
    case: GoldenCase
    generated_sql: str
    attempts: int
    recovered: Optional[bool]
    score: CaseScore
    ragas_equivalence: Optional[float] = None
    attempt_errors: List[str] = field(default_factory=list)


async def _generate_single_shot(case: GoldenCase) -> str:
    state: Dict[str, Any] = {
        "user_query": case.question,
        "refined_query": case.question,
        "selected_tables": case.selected_tables,
        "retry_count": 0,
    }
    out = await sql_generator_node(state)
    return out.get("generated_sql", "")


async def _generate_with_self_correction(case: GoldenCase) -> tuple[str, int, bool, List[str]]:
    """Regenerate on safety/execution failure, mirroring the graph edges."""
    state: Dict[str, Any] = {
        "user_query": case.question,
        "refined_query": case.question,
        "selected_tables": case.selected_tables,
        "retry_count": 0,
    }
    attempts = 0
    errors: List[str] = []
    sql = ""
    while attempts < _MAX_ATTEMPTS:
        out = await sql_generator_node(state)
        state.update(out)
        attempts += 1
        sql = state.get("generated_sql", "")

        is_safe, safety_msg = validate_sql_safety(sql)
        if not is_safe:
            errors.append(f"attempt {attempts}: unsafe ({safety_msg})")
            state["validation_error"] = safety_msg
            state["query_error"] = None
            if state.get("retry_count", 0) >= 3:
                return sql, attempts, False, errors
            continue

        state["validation_error"] = None
        ok, _rows, exec_err = safe_execute(sql)
        if not ok:
            errors.append(f"attempt {attempts}: exec error ({exec_err})")
            state["query_error"] = exec_err
            if state.get("retry_count", 0) >= 3:
                return sql, attempts, False, errors
            continue

        # Safe and executable -> stop.
        return sql, attempts, True, errors

    return sql, attempts, False, errors


async def run_case(case: GoldenCase, self_correct: bool) -> CaseResult:
    if self_correct:
        sql, attempts, recovered, errors = await _generate_with_self_correction(case)
    else:
        sql = await _generate_single_shot(case)
        attempts, recovered, errors = 1, None, []

    score = score_case(
        case_id=case.id,
        category=case.category,
        candidate_sql=sql,
        golden_sql=case.golden_sql,
        order_sensitive=case.order_sensitive,
    )

    ragas_score: Optional[float] = None
    if ragas_eval.ragas_enabled():
        schema_context = get_database_schema_string(case.selected_tables)
        ragas_score = await ragas_eval.score_sql_equivalence(
            candidate_sql=sql,
            golden_sql=case.golden_sql,
            schema_context=schema_context,
        )

    return CaseResult(
        case=case,
        generated_sql=sql,
        attempts=attempts,
        recovered=recovered,
        score=score,
        ragas_equivalence=ragas_score,
        attempt_errors=errors,
    )


async def run_all(self_correct: bool = False) -> List[CaseResult]:
    """Run every golden case sequentially (gentle on LLM rate limits)."""
    cases = load_cases()
    results: List[CaseResult] = []
    for i, case in enumerate(cases, start=1):
        print(f"[{i}/{len(cases)}] {case.id} ({case.category}) ...", flush=True)
        results.append(await run_case(case, self_correct))
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the SQL generator node.")
    parser.add_argument(
        "--self-correct",
        action="store_true",
        help="Enable the validator/executor self-correction retry loop.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for scorecard.json (defaults to backend/evals/scorecard.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    # Imported here to keep report generation out of the import path of run_all,
    # which the test suite imports directly.
    from app.evaluation.report import write_report

    results = asyncio.run(run_all(self_correct=args.self_correct))
    write_report(results, self_correct=args.self_correct, output_path=args.output)


if __name__ == "__main__":
    main()
