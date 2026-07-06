import re
from typing import Tuple

# Note: "REPLACE" is intentionally excluded - it is a legitimate read-only
# SQLite string function (REPLACE(x, y, z)). The REPLACE INTO statement form is
# already blocked by the "must start with SELECT/WITH" + single-statement rules.
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "GRANT", "REVOKE",
    "ATTACH", "DETACH", "PRAGMA", "CREATE", "VACUUM", "REINDEX",
]

ALLOWED_STARTS = ("SELECT", "WITH")


def _strip_comments(query: str) -> str:
    """Removes SQL comments so keywords cannot be hidden inside them."""
    # Remove block comments /* ... */ (including multi-line)
    without_block = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    # Remove line comments -- ... to end of line
    without_line = re.sub(r"--[^\n]*", " ", without_block)
    return without_line


def _strip_string_literals(query: str) -> str:
    """Removes quoted string literals so their contents are not scanned as SQL."""
    no_single = re.sub(r"'(?:[^']|'')*'", " ", query)
    no_double = re.sub(r'"(?:[^"]|"")*"', " ", no_single)
    return no_double


def validate_sql_safety(query: str) -> Tuple[bool, str]:
    """
    Validates that the SQL query is read-only and safe to execute.
    Returns (is_safe, error_message).
    """
    if not query or not query.strip():
        return False, "Empty SQL query."

    # Work on a comment-free copy for structural checks.
    sanitized = _strip_comments(query).strip()

    if not sanitized:
        return False, "SQL query contains no executable statements."

    # Enforce a single statement. A trailing semicolon is allowed, but anything
    # after it (a second statement) is not.
    statements = [s for s in sanitized.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Only a single SQL statement is allowed."

    # The query must be a read-only SELECT (optionally a CTE via WITH). Allow
    # leading parentheses, e.g. "(SELECT ...) UNION ALL (SELECT ...)".
    lead = sanitized.lstrip("( \t\r\n").upper()
    if not lead.startswith(ALLOWED_STARTS):
        return False, "Only read-only queries starting with SELECT or WITH are allowed."

    # Scan for forbidden keywords, ignoring string literals so legitimate data
    # values (e.g. a product named 'Update Kit') do not trip the check.
    scan_target = _strip_string_literals(sanitized).upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', scan_target):
            return False, f"SQL query contains forbidden keyword: {keyword}. Only read-only queries are allowed."

    return True, ""
