import re
from typing import Optional


SELECT_ONLY_PATTERN = re.compile(r"^\s*select\b", flags=re.IGNORECASE | re.DOTALL)
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|commit|rollback)\b",
    flags=re.IGNORECASE,
)
FORBIDDEN_CHARS = re.compile(r";|--|/\*|\*/", flags=re.IGNORECASE)
ALLOWED_TABLE = "products"


def is_select_only(sql: str) -> bool:
    """Ensure SQL starts with SELECT and contains no forbidden write/ddl keywords.

    This is a defensive guard; we also strip trailing semicolons and comments.
    """
    if not sql or not SELECT_ONLY_PATTERN.search(sql):
        return False
    if FORBIDDEN_KEYWORDS.search(sql):
        return False
    return True


def normalize_sql(sql: str) -> str:
    """Normalize SQL:
    - remove trailing semicolons
    - strip C-style and SQL line comments
    - collapse whitespace
    """
    if not sql:
        return sql
    # Remove C-style comments
    sql_no_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove line comments
    sql_no_comments = re.sub(r"--.*?$", " ", sql_no_block_comments, flags=re.MULTILINE)
    # Remove trailing semicolons
    sql_no_semicolon = re.sub(r";\s*$", "", sql_no_comments)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", sql_no_semicolon).strip()
    return normalized


def enforce_limit(sql: str, max_rows: int = 10) -> str:
    """Ensure a LIMIT clause not exceeding max_rows is present."""
    if not sql:
        return sql
    # If query already has a LIMIT, cap it
    limit_match = re.search(r"\blimit\s+(\d+)", sql, flags=re.IGNORECASE)
    if limit_match:
        try:
            current = int(limit_match.group(1))
            if current > max_rows:
                sql = re.sub(r"\blimit\s+\d+", f"LIMIT {max_rows}", sql, flags=re.IGNORECASE)
            return sql
        except ValueError:
            pass
    # Append LIMIT if missing
    return f"{sql} LIMIT {max_rows}"


def validate_sql_safe(sql: str) -> Optional[str]:
    """Return an error string if unsafe, else None."""
    if not is_select_only(sql):
        return "Only SELECT statements are allowed."
    if FORBIDDEN_CHARS.search(sql):
        return "Potentially unsafe SQL characters detected."
    # Enforce only the products table is referenced (simple guard)
    # Accept forms like FROM products p, JOIN products AS p, etc.
    # Disallow other tables or schemas by checking tokens after FROM/JOIN keywords.
    lowered = sql.lower()
    from_matches = re.findall(r"\bfrom\s+([a-zA-Z0-9_\.]+)", lowered)
    join_matches = re.findall(r"\bjoin\s+([a-zA-Z0-9_\.]+)", lowered)
    referenced = set(from_matches + join_matches)
    if not referenced:
        return "Query must reference the products table."
    for name in referenced:
        # Strip optional schema
        base = name.split(".")[-1]
        if base != ALLOWED_TABLE:
            return "Only the products table is allowed."
    return None


