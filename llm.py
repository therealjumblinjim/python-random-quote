"""LLM helpers for natural-language-to-SQL and results explanation."""

from __future__ import annotations

import os
import re

from openai import OpenAI


class LLMError(RuntimeError):
    """Raised when the model returns invalid SQL or malformed output."""


FORBIDDEN_SQL_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\bmerge\b",
    r"\bexec\b",
    r"\bexecute\b",
]


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not set. Add it to your .env file first.")
    return OpenAI(api_key=api_key)


def validate_select_only_sql(sql: str) -> str:
    """Allow only a single SELECT statement (or CTE + SELECT)."""
    normalized = sql.strip().strip("`").strip()
    lower = normalized.lower()

    if not lower:
        raise LLMError("Model returned empty SQL.")

    if ";" in lower[:-1]:
        raise LLMError("Multiple SQL statements are not allowed.")

    if not (lower.startswith("select") or lower.startswith("with")):
        raise LLMError("Only SELECT queries are allowed.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, lower):
            raise LLMError(f"Forbidden SQL operation detected: {pattern}")

    return normalized.rstrip(";")


def generate_sql(question: str, schema_context: str) -> str:
    """Generate read-only SQL from a user question and schema context."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = (
        "You are a SQL Server assistant. Return exactly one read-only SQL query. "
        "Output SQL text only, no markdown and no explanation. "
        "Rules: only SELECT/CTE statements, include TOP 100 unless user asks for fewer."
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Schema context:\n{schema_context}\n\n"
        "Return one SQL Server query now."
    )

    response = _client().responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    sql = (response.output_text or "").strip()
    return validate_select_only_sql(sql)


def explain_results(question: str, query: str, rows: list[dict]) -> str:
    """Turn query results into a concise, beginner-friendly explanation."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    sample_rows = rows[:10]

    system_prompt = (
        "You explain SQL query results clearly for a beginner. "
        "Be concise and mention if results are truncated."
    )
    user_prompt = (
        f"Original question: {question}\n"
        f"SQL used: {query}\n"
        f"Sample rows (max 10): {sample_rows}\n"
        f"Total rows returned to app: {len(rows)}"
    )

    response = _client().responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return (response.output_text or "").strip()
