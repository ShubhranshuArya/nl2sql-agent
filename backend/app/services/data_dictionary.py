"""Loads the canonical data dictionary and exposes scoped views for agents.

The dictionary (context/data_dictionary.yaml) is the single source of truth for
database *semantics* - domain description, column meanings, enum values,
relationships, and query notes. Structural facts (real table/column names and
types) are still read live from the database via app.tools.sql, so this file
only augments the live schema with meaning.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.tools.sql import get_table_schema

_DEFAULT_PATH = Path(__file__).parents[3] / "context" / "data_dictionary.yaml"


def _dictionary_path() -> Path:
    override = os.getenv("DATA_DICTIONARY_PATH")
    return Path(override) if override else _DEFAULT_PATH


@lru_cache(maxsize=1)
def _load() -> Dict:
    path = _dictionary_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_domain_description() -> str:
    """Returns the canonical one-paragraph description of the database domain."""
    return (_load().get("domain") or "").strip()


def get_table_catalog() -> str:
    """Returns a `table_name - one-line description` listing of all tables."""
    tables = _load().get("tables", {})
    lines = []
    for name, meta in tables.items():
        description = (meta or {}).get("description", "").strip()
        lines.append(f"- {name}: {description}" if description else f"- {name}")
    return "\n".join(lines)


def _format_columns(meta: Dict) -> str:
    columns = (meta or {}).get("columns", {})
    lines = []
    for col, col_meta in columns.items():
        col_meta = col_meta or {}
        parts = []
        col_type = col_meta.get("type")
        if col_type:
            parts.append(str(col_type))
        description = col_meta.get("description")
        if description:
            parts.append(description)
        enum = col_meta.get("enum")
        if enum:
            parts.append("one of: " + ", ".join(str(v) for v in enum))
        detail = " | ".join(parts)
        lines.append(f"  - {col}: {detail}" if detail else f"  - {col}")
    return "\n".join(lines)


def _relationships_for(tables: List[str]) -> List[str]:
    table_set = set(tables)
    rels = []
    for rel in _load().get("relationships", []):
        frm = rel.get("from", "")
        to = rel.get("to", "")
        frm_table = frm.split(".")[0]
        to_table = to.split(".")[0]
        if frm_table in table_set and to_table in table_set:
            cardinality = rel.get("cardinality", "")
            line = f"  - {frm} -> {to} ({cardinality})".rstrip(" ()")
            note = rel.get("note")
            if note:
                line += f" - {note}"
            rels.append(line)
    return rels


def get_schema_context(tables: Optional[List[str]] = None) -> str:
    """Builds rich schema context for the selected tables.

    Combines the live CREATE TABLE statement (authoritative structure) with the
    dictionary's column descriptions, enum values, cross-table relationships, and
    global query notes. Falls back gracefully when the dictionary lacks an entry.
    """
    data = _load()
    dict_tables = data.get("tables", {})

    if not tables:
        tables = list(dict_tables.keys())

    sections = []
    for table in tables:
        meta = dict_tables.get(table, {})
        parts = [f"## Table: {table}"]

        description = (meta or {}).get("description", "").strip()
        if description:
            parts.append(description)

        ddl = get_table_schema(table)
        if ddl:
            parts.append("Schema (DDL):\n" + ddl)

        columns = _format_columns(meta)
        if columns:
            parts.append("Columns:\n" + columns)

        sections.append("\n".join(parts))

    relationships = _relationships_for(tables)
    if relationships:
        sections.append("## Relationships (join keys)\n" + "\n".join(relationships))

    notes = data.get("notes", [])
    if notes:
        sections.append("## Notes for query generation\n" + "\n".join(f"- {n}" for n in notes))

    return "\n\n".join(sections)
