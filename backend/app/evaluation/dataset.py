"""Loads and validates the golden SQL dataset for the SQL generator eval.

Each line of ``backend/evals/golden_sql.jsonl`` is one case with the shape::

    {
      "id": "sql01_single_filter",       # unique, stable identifier
      "category": "single_table_filter",  # coarse SQL category for reporting
      "question": "...",                  # natural-language prompt for the node
      "selected_tables": ["products"],    # fixture normally set by table_selector
      "order_sensitive": false,            # compare result rows in order?
      "golden_sql": "SELECT ..."          # reference query (must be read-only)
    }

The loader validates structure and (optionally) that each ``golden_sql`` passes
the app's safety validator and executes against the built database, so the
golden set itself is trustworthy before it is used to judge the model.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.tools.sql import execute_read_query
from app.tools.validator import validate_sql_safety

_DEFAULT_PATH = Path(__file__).parents[2] / "evals" / "golden_sql.jsonl"

_REQUIRED_FIELDS = ("id", "category", "question", "selected_tables", "golden_sql")


@dataclass
class GoldenCase:
    """A single golden evaluation case."""

    id: str
    category: str
    question: str
    selected_tables: List[str]
    golden_sql: str
    order_sensitive: bool = False


@dataclass
class DatasetValidation:
    """Result of validating the golden dataset against the live database."""

    ok: bool
    errors: List[str] = field(default_factory=list)


def dataset_path(path: Optional[Path] = None) -> Path:
    return path or _DEFAULT_PATH


def load_cases(path: Optional[Path] = None) -> List[GoldenCase]:
    """Parses the JSONL dataset into GoldenCase objects with structural checks."""
    p = dataset_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Golden dataset not found at {p}")

    cases: List[GoldenCase] = []
    seen_ids: set[str] = set()
    with open(p, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {lineno}: invalid JSON ({e})") from e

            missing = [k for k in _REQUIRED_FIELDS if k not in obj]
            if missing:
                raise ValueError(f"Line {lineno}: missing fields {missing}")
            if not isinstance(obj["selected_tables"], list) or not obj["selected_tables"]:
                raise ValueError(f"Line {lineno}: 'selected_tables' must be a non-empty list")
            if obj["id"] in seen_ids:
                raise ValueError(f"Line {lineno}: duplicate id '{obj['id']}'")
            seen_ids.add(obj["id"])

            cases.append(
                GoldenCase(
                    id=obj["id"],
                    category=obj["category"],
                    question=obj["question"],
                    selected_tables=list(obj["selected_tables"]),
                    golden_sql=obj["golden_sql"],
                    order_sensitive=bool(obj.get("order_sensitive", False)),
                )
            )

    if not cases:
        raise ValueError(f"Golden dataset {p} contains no cases")
    return cases


def validate_dataset(cases: Optional[List[GoldenCase]] = None) -> DatasetValidation:
    """Checks every golden_sql is safe and executes against the database.

    Used both as a standalone integrity check and by the dataset unit test so a
    broken reference query is caught before it silently fails an eval run.
    """
    cases = cases if cases is not None else load_cases()
    errors: List[str] = []
    for case in cases:
        is_safe, msg = validate_sql_safety(case.golden_sql)
        if not is_safe:
            errors.append(f"[{case.id}] golden_sql failed safety check: {msg}")
            continue
        try:
            execute_read_query(case.golden_sql)
        except Exception as e:  # noqa: BLE001 - surface any execution failure
            errors.append(f"[{case.id}] golden_sql failed to execute: {e}")
    return DatasetValidation(ok=not errors, errors=errors)


if __name__ == "__main__":
    loaded = load_cases()
    result = validate_dataset(loaded)
    print(f"Loaded {len(loaded)} golden cases from {dataset_path()}")
    if result.ok:
        print("All golden_sql statements are safe and executable.")
    else:
        print("Validation errors:")
        for err in result.errors:
            print(f"  - {err}")
        raise SystemExit(1)
