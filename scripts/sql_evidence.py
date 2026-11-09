"""Run SQL statements on a Databricks SQL warehouse and write the results to evidence/ as text.

    python3 scripts/sql_evidence.py evidence/01_lakeflow_row_counts.md 02_unity_catalog/governance.sql
    python3 scripts/sql_evidence.py evidence/x.md -e "SELECT 1"

Each statement and its result table (or error) is written to the markdown file, so the
evaluator can read exactly what ran and what came back.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys

PROFILE = "fe-east"
WAREHOUSE_ID = "148ccb90800933a1"


def run(sql: str) -> dict:
    body = json.dumps({"warehouse_id": WAREHOUSE_ID, "statement": sql, "wait_timeout": "50s",
                       "catalog": "users", "schema": "narasimha_kamathardi"})
    p = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", PROFILE,
                        "--json", body], capture_output=True, text=True)
    out = p.stdout if "{" in p.stdout else p.stderr
    return json.JSONDecoder().raw_decode(out[out.find("{"):])[0]


def split(text: str) -> list[str]:
    stmts, cur = [], []
    for line in text.splitlines():
        if line.strip().startswith("--") and not cur:
            continue
        cur.append(line)
        if line.rstrip().endswith(";"):
            s = "\n".join(cur).strip().rstrip(";").strip()
            if s:
                stmts.append(s)
            cur = []
    if "\n".join(cur).strip():
        stmts.append("\n".join(cur).strip())
    return stmts


def as_markdown(r: dict, limit: int) -> str:
    st = r.get("status", {})
    if st.get("state") != "SUCCEEDED":
        return f"**{st.get('state')}**: {st.get('error', {}).get('message', r)}\n"
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = r.get("result", {}).get("data_array", []) or []
    if not cols:
        return "OK\n"
    md = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for row in rows[:limit]:
        md += "| " + " | ".join("" if v is None else str(v) for v in row) + " |\n"
    total = r.get("manifest", {}).get("total_row_count", len(rows))
    return md + f"\n({total} rows{', showing first %d' % limit if total > limit else ''})\n"


ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("sql_file", nargs="?")
ap.add_argument("-e", "--execute", action="append", default=[])
ap.add_argument("--title", default=None)
ap.add_argument("--limit", type=int, default=25)
a = ap.parse_args()

stmts = split(open(a.sql_file).read()) if a.sql_file else []
stmts += [s.strip().rstrip(";") for s in a.execute]
doc = f"# {a.title or a.out}\n\nExecuted {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M UTC} on warehouse " \
      f"`{WAREHOUSE_ID}` (fe-east) via the SQL Statement API.\n\n"
failed = 0
for s in stmts:
    r = run(s)
    failed += r.get("status", {}).get("state") != "SUCCEEDED"
    doc += f"```sql\n{s}\n```\n\n{as_markdown(r, a.limit)}\n"
open(a.out, "w").write(doc)
print(f"wrote {a.out}: {len(stmts)} statements, {failed} failed")
sys.exit(1 if failed else 0)
