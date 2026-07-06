from typing import List

from app.tools.sql import get_table_names
from app.services.data_dictionary import get_schema_context


def get_database_schema_string(table_names: List[str] = None) -> str:
    """
    Returns rich schema context for the specified tables, combining the live
    database DDL with the data dictionary's descriptions, enums, relationships,
    and query notes. If no tables are specified, returns context for all tables.
    """
    return get_schema_context(table_names)


def get_all_table_names_formatted() -> str:
    """Returns a comma-separated string of all table names."""
    return ", ".join(get_table_names())
