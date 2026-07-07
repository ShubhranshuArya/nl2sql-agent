"""Aggregates SQL-generator eval results into a scorecard (JSON + markdown).

Deterministic metrics are the headline; the optional RAGAS equivalence score is
reported alongside as a supplementary signal and is never used to pass/fail.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.evaluation.metrics import aggregate
from app.evaluation.ragas_eval import summarize as summarize_ragas

if TYPE_CHECKING:
    from app.evaluation.runner import CaseResult

_DEFAULT_OUTPUT = Path(__file__).parents[2] / "evals" / "scorecard.json"


def build_scorecard(results: List["CaseResult"], self_correct: bool = False) -> Dict[str, Any]:
    """Build the structured scorecard from a list of CaseResult objects."""
    scores = [r.score for r in results]
    agg = aggregate(scores)

    ragas_summary = summarize_ragas([r.ragas_equivalence for r in results])

    per_case: List[Dict[str, Any]] = []
    for r in results:
        entry: Dict[str, Any] = {
            "id": r.case.id,
            "category": r.case.category,
            "execution_match": r.score.execution_match,
            "is_safe": r.score.is_safe,
            "executed": r.score.executed,
            "exact_result_match": r.score.exact_result_match,
            "attempts": r.attempts,
            "generated_sql": r.generated_sql,
            "notes": r.score.notes,
        }
        if self_correct:
            entry["recovered"] = r.recovered
            entry["attempt_errors"] = r.attempt_errors
        if r.ragas_equivalence is not None:
            entry["ragas_equivalence"] = r.ragas_equivalence
        per_case.append(entry)

    scorecard: Dict[str, Any] = {
        "mode": "self_correct" if self_correct else "single_shot",
        "deterministic": agg,
        "per_case": per_case,
    }

    if self_correct:
        recovered = [r for r in results if r.recovered]
        attempts = [r.attempts for r in results]
        scorecard["self_correction"] = {
            "recovery_rate": round(len(recovered) / len(results), 4) if results else 0.0,
            "avg_attempts": round(sum(attempts) / len(attempts), 2) if attempts else 0.0,
        }

    if ragas_summary is not None:
        scorecard["ragas_llm_sql_equivalence"] = ragas_summary

    return scorecard


def render_markdown(scorecard: Dict[str, Any]) -> str:
    """Render a human-readable markdown summary of the scorecard."""
    overall = scorecard["deterministic"]["overall"]
    lines: List[str] = []
    lines.append("# SQL Generator Evaluation Scorecard")
    lines.append("")
    lines.append(f"Mode: `{scorecard['mode']}`  |  Cases: {overall['n_cases']}")
    lines.append("")
    lines.append("## Overall (deterministic)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Execution accuracy | {overall['execution_accuracy']:.2%} |")
    lines.append(f"| Safety rate | {overall['safety_rate']:.2%} |")
    lines.append(f"| Executability rate | {overall['executability_rate']:.2%} |")
    lines.append(f"| Exact result match | {overall['exact_result_match_rate']:.2%} |")

    if "self_correction" in scorecard:
        sc = scorecard["self_correction"]
        lines.append(f"| Recovery rate | {sc['recovery_rate']:.2%} |")
        lines.append(f"| Avg attempts | {sc['avg_attempts']} |")

    if "ragas_llm_sql_equivalence" in scorecard:
        rg = scorecard["ragas_llm_sql_equivalence"]
        lines.append(
            f"| RAGAS SQL equivalence (mean, n={rg['n_scored']}) | {rg['mean_equivalence']:.2%} |"
        )

    lines.append("")
    lines.append("## By category")
    lines.append("")
    lines.append("| Category | Cases | Exec accuracy | Safety | Executable |")
    lines.append("| --- | --- | --- | --- | --- |")
    for cat, m in scorecard["deterministic"]["by_category"].items():
        lines.append(
            f"| {cat} | {m['n_cases']} | {m['execution_accuracy']:.2%} | "
            f"{m['safety_rate']:.2%} | {m['executability_rate']:.2%} |"
        )

    lines.append("")
    lines.append("## Per-case")
    lines.append("")
    lines.append("| ID | Category | Match | Safe | Exec | Attempts | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for c in scorecard["per_case"]:
        mark = "yes" if c["execution_match"] else "no"
        safe = "yes" if c["is_safe"] else "no"
        ex = "yes" if c["executed"] else "no"
        notes = "; ".join(c["notes"]) if c["notes"] else ""
        lines.append(
            f"| {c['id']} | {c['category']} | {mark} | {safe} | {ex} | "
            f"{c['attempts']} | {notes} |"
        )

    return "\n".join(lines) + "\n"


def write_report(
    results: List["CaseResult"],
    self_correct: bool = False,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Write scorecard.json + a sibling markdown file and print the summary."""
    scorecard = build_scorecard(results, self_correct=self_correct)

    out = Path(output_path) if output_path else _DEFAULT_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")

    md = render_markdown(scorecard)
    md_path = out.with_suffix(".md")
    md_path.write_text(md, encoding="utf-8")

    print("\n" + md)
    print(f"Wrote {out}")
    print(f"Wrote {md_path}")
    return scorecard
