"""Optional, flag-gated RAGAS SQL semantic-equivalence scoring.

This is a *supplementary* signal, not a CI gate. Because the eval scope is SQL
generation (there is no natural-language answer to check), the relevant RAGAS
metric is ``LLMSQLEquivalence``: it asks an LLM whether the generated SQL is
semantically equivalent to the reference SQL, given the schema. It is useful for
explaining cases where execution accuracy fails on a textual difference that is
actually equivalent, or vice versa.

Design constraints:
- Runs only when ``EVAL_RAGAS`` is truthy.
- ``ragas`` and ``langchain-openai`` are imported lazily so the core app and the
  deterministic eval path never depend on them being installed.
- Reuses the existing ``LLM_*`` configuration (LLM-only, no embeddings).
"""
from __future__ import annotations

import os
from typing import List, Optional

from app.services.llm import get_model


def ragas_enabled() -> bool:
    """True when the optional RAGAS layer is switched on via env."""
    return os.getenv("EVAL_RAGAS", "0").strip().lower() in ("1", "true", "yes")


class RagasUnavailable(RuntimeError):
    """Raised when RAGAS is requested but its dependencies are missing."""


_metric = None  # cached LLMSQLEquivalence metric with an attached LLM


def _build_metric():
    """Lazily construct the LLMSQLEquivalence metric bound to the LLM_* endpoint.

    Imports happen inside the function on purpose: absence of ragas /
    langchain-openai must never break importing this module or the core app.
    """
    global _metric
    if _metric is not None:
        return _metric

    try:
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import LLMSQLEquivalence
    except ImportError as e:  # pragma: no cover - depends on optional extras
        raise RagasUnavailable(
            "RAGAS extras not installed. Run `uv sync --extra eval` "
            "(or `pip install ragas langchain-openai`) to enable EVAL_RAGAS."
        ) from e

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or None

    chat = ChatOpenAI(
        model=get_model(),
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )
    metric = LLMSQLEquivalence()
    metric.llm = LangchainLLMWrapper(chat)
    _metric = metric
    return _metric


async def score_sql_equivalence(
    candidate_sql: str,
    golden_sql: str,
    schema_context: str,
) -> Optional[float]:
    """Return a semantic-equivalence score (1.0 equivalent / 0.0 not), or None.

    Returns None when RAGAS is disabled or a scoring error occurs; callers treat
    None as "not evaluated" and never fail on it.
    """
    if not ragas_enabled():
        return None

    try:
        from ragas.dataset_schema import SingleTurnSample

        metric = _build_metric()
        sample = SingleTurnSample(
            response=candidate_sql,
            reference=golden_sql,
            reference_contexts=[schema_context],
        )
        score = await metric.single_turn_ascore(sample)
        return float(score)
    except RagasUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - supplementary metric must not crash a run
        print(f"[ragas] SQL equivalence scoring failed: {e}")
        return None


def summarize(scores: List[Optional[float]]) -> Optional[dict]:
    """Aggregate equivalence scores, ignoring cases that were not evaluated."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return {
        "n_scored": len(valid),
        "mean_equivalence": round(sum(valid) / len(valid), 4),
        "equivalent_count": sum(1 for s in valid if s >= 0.5),
    }
