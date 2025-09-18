import os
from typing import Optional
from dotenv import load_dotenv

from openai import OpenAI

from utils import enforce_limit, normalize_sql, validate_sql_safe


# Ensure .env values override any pre-existing env vars set in the shell/conda env
load_dotenv(override=True)


SYSTEM_PROMPT = (
    "You are a senior data engineer that writes safe, read-only SQL for PostgreSQL. "
    "Rules: Only produce a single SELECT statement; never include INSERT, UPDATE, DELETE, or DDL. "
    "Do not include comments. Always use ILIKE for fuzzy text matching when appropriate. "
    "Always constrain results with LIMIT 10 by default. "
    "Table schema: products(sku TEXT, description TEXT, price FLOAT, currency TEXT, family TEXT, status TEXT)."
)


def _build_user_prompt(nl_query: str) -> str:
    example = (
        'User query: "I need a camera for outdoor"\n'
        'SQL:\n'
        "SELECT * FROM products WHERE description ILIKE '%outdoor%' AND family ILIKE '%camera%' LIMIT 10;"
    )
    return f"{example}\n\nUser query: \"{nl_query}\"\nSQL:"


def generate_sql_from_nl(nl_query: str) -> Optional[str]:
    """Use GPT-4o to translate NL to safe SELECT SQL. Returns None if failed."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    # Use responses API to get a short completion that is just the SQL
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(nl_query)},
        ],
        temperature=0,
        max_tokens=200,
    )

    text = response.choices[0].message.content if response.choices else None
    if not text:
        return None

    # Extract SQL: remove code fences and labels
    cleaned = text.strip()
    if cleaned.lower().startswith("sql:"):
        cleaned = cleaned[4:].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # If the first line is 'sql', drop it
        lines = [line for line in cleaned.splitlines() if line.strip()]
        if lines and lines[0].strip().lower() == "sql":
            lines = lines[1:]
        cleaned = "\n".join(lines)

    sql = cleaned
    # Normalize and enforce safety constraints
    sql = normalize_sql(sql)
    sql = enforce_limit(sql, max_rows=10)
    error = validate_sql_safe(sql)
    if error:
        return None
    return sql


