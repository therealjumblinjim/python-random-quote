"""CLI app: ask natural-language questions against local MSSQL safely."""

from __future__ import annotations

from dotenv import load_dotenv

from db import DatabaseError, fetch_schema_context, run_select_query
from llm import LLMError, explain_results, generate_sql


def main() -> None:
    load_dotenv()
    print("Natural Language SQL Assistant (MSSQL)")
    print("Type 'exit' to quit.\n")

    try:
        schema_context = fetch_schema_context()
    except DatabaseError as exc:
        print(f"Database setup error: {exc}")
        return

    print("Schema loaded. You can now ask questions like:")
    print("  - 'Show top 10 customers by total spend this year'\n")

    while True:
        question = input("Question> ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not question:
            continue

        try:
            sql = generate_sql(question, schema_context)
            print(f"\nGenerated SQL:\n{sql}\n")

            result = run_select_query(sql, max_rows=100)
            rows = result["rows"]

            print(f"Rows returned: {result['row_count']}")
            if rows:
                print("First row:")
                print(rows[0])
            else:
                print("No rows matched.")

            explanation = explain_results(question, sql, rows)
            print("\nExplanation:")
            print(explanation)
            print("\n" + "-" * 60 + "\n")

        except (LLMError, DatabaseError) as exc:
            print(f"Error: {exc}\n")


if __name__ == "__main__":
    main()
