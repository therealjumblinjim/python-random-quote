# Let's Write a Python Quote Bot!

This repository will get you started with building a quote bot in Python. It's meant to be used along with the [Learning Lab](https://lab.github.com) intro to Python.

When complete, you'll be able to grab random quotes from the command line, like this:

> **$** python get-quote.py
> 
> Keep it logically awesome
> 
> **$** python get-quote.py
> 
> Speak like a human

## Start the Tutorial

You can find your next step in [this repo's issues](../../issues/)!

## Beginner Guide: Connect to Local MSSQL + Natural Language Queries

If you're new to this, think about it in **two layers**:

1. **Database connectivity** (ODBC): your app can connect to SQL Server.
2. **Natural language layer** (LLM): translates plain English into SQL, runs it, then explains results.

OpenAI (or any LLM) does **not** directly "read" your database objects by itself. Your application must:

* connect to MSSQL,
* fetch schema metadata (tables/columns),
* pass that schema context to the model,
* execute generated SQL safely.

### 1) Install prerequisites

#### SQL Server + ODBC driver

* Ensure your SQL Server instance is running locally.
* Install an ODBC Driver for SQL Server (typically **ODBC Driver 18 for SQL Server**).

#### Python packages

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pyodbc sqlalchemy openai python-dotenv
```

### 2) Build your ODBC connection string

For local SQL Server with username/password:

```text
DRIVER={ODBC Driver 18 for SQL Server};
SERVER=localhost,1433;
DATABASE=YourDatabaseName;
UID=YourUser;
PWD=YourPassword;
TrustServerCertificate=yes;
Encrypt=yes;
```

For Windows integrated auth, use:

```text
Trusted_Connection=yes;
```

Store secrets in `.env` (never commit real passwords):

```env
MSSQL_ODBC_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=YourDatabaseName;UID=YourUser;PWD=YourPassword;TrustServerCertificate=yes;Encrypt=yes;
OPENAI_API_KEY=your_key_here
```

### 3) Test the MSSQL connection first

Use this minimal script to verify connectivity:

```python
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()
conn_str = os.environ["MSSQL_ODBC_CONN_STR"]

with pyodbc.connect(conn_str) as conn:
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 name FROM sys.tables ORDER BY name")
    row = cur.fetchone()
    print("Connected. Example table:", row[0] if row else "No tables found")
```

If this fails, fix connection/driver/auth issues before touching the LLM layer.

### 4) Provide schema context to the model

Before asking for SQL generation, collect schema metadata such as:

* table names,
* column names and types,
* relationships/foreign keys.

You can query SQL Server system views like `INFORMATION_SCHEMA.TABLES` and `INFORMATION_SCHEMA.COLUMNS`.

### 5) Safe natural language query flow

Recommended flow:

1. User asks a question in English.
2. Your app sends the question + schema context to the model.
3. Model returns a **read-only SQL query**.
4. Your app validates SQL safety (allow only `SELECT`, no `INSERT/UPDATE/DELETE/DROP`).
5. Execute query via ODBC.
6. Send rows back to model for a plain-English explanation.

### 6) Important safety rules (especially for novices)

* Use a **read-only DB user** for LLM-generated queries.
* Add server-side query timeout limits.
* Limit returned row counts (`TOP 100`, pagination).
* Log generated SQL for review.
* Start with a non-production database.

### 7) Minimal architecture you can build next

* `db.py` — ODBC connect + schema fetch + SQL execution
* `llm.py` — prompt creation + OpenAI call
* `app.py` — CLI loop: ask question -> generate SQL -> validate -> run -> summarize

---

If you want, the next step can be adding these files directly in this repository with a small command-line prototype you can run locally.

## Run a working prototype in this repo

I added a minimal command-line prototype:

* `db.py` — connection, schema loading, query execution
* `llm.py` — SQL generation, SELECT-only validation, explanation
* `app.py` — interactive CLI loop

### Quick start

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pyodbc openai python-dotenv
```

2. Add `.env` in the repository root. You can choose **either** style:

**Style A: one full connection string**

```env
MSSQL_ODBC_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=YourDatabaseName;UID=YourUser;PWD=YourPassword;TrustServerCertificate=yes;Encrypt=yes;
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
DB_QUERY_TIMEOUT_SECONDS=30
```

**Style B: split values (easier for beginners)**

```env
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_SERVER=localhost,1433
MSSQL_DATABASE=YourDatabaseName
MSSQL_UID=YourUser
MSSQL_PWD=YourPassword
MSSQL_ENCRYPT=yes
MSSQL_TRUST_SERVER_CERT=yes
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
DB_QUERY_TIMEOUT_SECONDS=30
```

> Yes — the ODBC driver name goes in `MSSQL_ODBC_DRIVER` (Style B) or inside `DRIVER={...}` in `MSSQL_ODBC_CONN_STR` (Style A).

3. Run the assistant:

```bash
python app.py
```

4. Ask questions in plain English, for example:

* "Show the top 10 orders by total amount"
* "How many users signed up this month?"

### Important notes

* This prototype is intentionally **read-only** and blocks dangerous SQL keywords.
* Use a read-only SQL login whenever possible.
* Results are capped (fetches up to 100 rows per query).
