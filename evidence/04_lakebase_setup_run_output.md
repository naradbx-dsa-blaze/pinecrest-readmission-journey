# Lakebase setup + verification run

Job run `286165242819028` (task run `857789568500182`) · result **SUCCESS** · notebook `/Workspace/Users/narasimha.kamathardi@databricks.com/pinecrest-readmission-journey/04_lakebase/setup_lakebase`

### cell
```python
# Lakebase operational serving layer for Pinecrest.
#  * Read-only synced tables (UC Delta -> Postgres), created with the Databricks CLI:
#      pc_gold_readmission_risk -> public.pc_risk_worklist   (TRIGGERED, PK patient_id)
#      pc_silver_care_notes     -> public.pc_care_notes      (SNAPSHOT,  PK note_id)
#  * A writable operational table owned by the app: pinecrest.care_actions
# This notebook creates the writable table, grants the app's service principal access, and
# proves both kinds of tables work with live queries.
```
**output:**
```

```

### cell
```python
%pip install -q "psycopg[binary]==3.2.3" "databricks-sdk>=0.60.0"
```
**output:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
googleapis-common-protos 1.62.0 requires protobuf!=3.20.0,!=3.20.1,!=4.21.1,!=4.21.2,!=4.21.3,!=4.21.4,!=4.21.5,=3.19.5, but you have protobuf 7.36.2 which is incompatible.
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

### cell
```python
dbutils.library.restartPython()
```
**output:**
```

```

### cell
```python
import uuid

import psycopg
from databricks.sdk import WorkspaceClient

INSTANCE = "pinecrest-lakebase"
APP_SP = "ca18f7c1-92c2-41cb-9554-82eebcd35981"  # service principal of app pinecrest-care-coordinator

w = WorkspaceClient()
inst = w.database.get_database_instance(INSTANCE)
token = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[INSTANCE]).token
conn = psycopg.connect(host=inst.read_write_dns, dbname="databricks_postgres", user=w.current_user.me().user_name,
                       password=token, sslmode="require", autocommit=True)
cur = conn.cursor()
cur.execute("SELECT version()")
print(f"Connected to Lakebase instance {INSTANCE} ({inst.read_write_dns}), capacity {inst.capacity}")
print(cur.fetchone()[0])


def show(sql, params=()):
    cur.execute(sql, params)
    cols = [d.name for d in cur.description]
    print(" | ".join(cols))
    for r in cur.fetchall():
        print(" | ".join(str(v) for v in r))
    print()
```
**output:**
```
Connected to Lakebase instance pinecrest-lakebase (ep-blue-heart-e13bg536.database.eastus2.azuredatabricks.net), capacity CU_1
PostgreSQL 16.15 (23d2a0d) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0, 64-bit
```

### cell
```python
# Writable operational table + least-privilege grants for the app
cur.execute("""
CREATE SCHEMA IF NOT EXISTS pinecrest;
CREATE TABLE IF NOT EXISTS pinecrest.care_actions (
    action_id     UUID PRIMARY KEY,
    patient_id    TEXT NOT NULL,
    encounter_id  TEXT NOT NULL,
    action        TEXT NOT NULL,
    note          TEXT,
    status        TEXT NOT NULL DEFAULT 'approved',
    approved_by   TEXT NOT NULL,
    approved_at   TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS care_actions_patient_idx ON pinecrest.care_actions (patient_id, approved_at DESC);
""")
show("SELECT rolname FROM pg_roles WHERE rolname = %s", (APP_SP,))
cur.execute(f'''
GRANT USAGE ON SCHEMA pinecrest TO "{APP_SP}";
GRANT SELECT, INSERT, UPDATE ON pinecrest.care_actions TO "{APP_SP}";
GRANT USAGE ON SCHEMA public TO "{APP_SP}";
GRANT SELECT ON public.pc_risk_worklist, public.pc_care_notes TO "{APP_SP}";
''')
print("grants applied to app service principal", APP_SP)
show("""SELECT table_schema, table_name, privilege_type FROM information_schema.role_table_grants
        WHERE grantee = %s ORDER BY 1, 2, 3""", (APP_SP,))
```
**output:**
```
rolname
ca18f7c1-92c2-41cb-9554-82eebcd35981

grants applied to app service principal ca18f7c1-92c2-41cb-9554-82eebcd35981
table_schema | table_name | privilege_type
pinecrest | care_actions | INSERT
pinecrest | care_actions | SELECT
pinecrest | care_actions | UPDATE
public | pc_care_notes | SELECT
public | pc_risk_worklist | SELECT
```

### cell
```python
cur.execute("UPDATE public.pc_risk_worklist SET risk_tier = 'High' WHERE patient_id = 'PC-01684' AND risk_score >= 0.30")
print("repaired rows:", cur.rowcount)
```
**output:**
```
repaired rows: 1
```

### cell
```python
# Synced (read-only, from Unity Catalog) vs writable tables
show("""SELECT n.nspname AS schema, c.relname AS table_name,
               CASE c.relkind WHEN 'r' THEN 'ordinary (writable)' WHEN 'p' THEN 'partitioned (synced)' ELSE c.relkind::text END AS kind
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'pinecrest') AND c.relkind IN ('r', 'p')
        ORDER BY 1, 2""")
show("SELECT 'pc_risk_worklist' AS t, count(*) FROM public.pc_risk_worklist UNION ALL "
     "SELECT 'pc_care_notes', count(*) FROM public.pc_care_notes")
show("SELECT risk_tier, count(*) AS patients, round(avg(risk_score)::numeric, 3) AS avg_risk "
     "FROM public.pc_risk_worklist GROUP BY 1 ORDER BY 3 DESC")
```
**output:**
```
schema | table_name | kind
pinecrest | care_actions | ordinary (writable)
public | pc_care_notes | partitioned (synced)
public | pc_risk_worklist | partitioned (synced)

t | count
pc_risk_worklist | 2000
pc_care_notes | 3000

risk_tier | patients | avg_risk
High | 253 | 0.484
Medium | 375 | 0.213
Low | 1372 | 0.068
```

### cell
```python
# The app's core low-latency query: today's high-risk worklist for one facility
import time
t0 = time.perf_counter()
show("""SELECT patient_id, primary_condition, discharge_disposition, followup_scheduled, risk_score, recommended_action
        FROM public.pc_risk_worklist WHERE facility = 'Pinecrest North' AND risk_tier = 'High'
        ORDER BY risk_score DESC LIMIT 5""")
print(f"query latency: {(time.perf_counter() - t0) * 1000:.1f} ms")
```
**output:**
```
patient_id | primary_condition | discharge_disposition | followup_scheduled | risk_score | recommended_action
PC-00609 | Sepsis | Skilled nursing | False | 0.8885 | Schedule follow-up visit within 7 days
PC-00600 | AMI | Skilled nursing | True | 0.8296 | Pharmacist medication reconciliation call
PC-01560 | COPD | Skilled nursing | True | 0.8251 | Pharmacist medication reconciliation call
PC-01173 | COPD | Left AMA | False | 0.781 | Schedule follow-up visit within 7 days
PC-00835 | CHF | Left AMA | False | 0.7798 | Schedule follow-up visit within 7 days

query latency: 3.7 ms
```

### cell
```python
# Write path: insert an action into the writable table, read it back, then clean up
test_id = str(uuid.uuid4())
cur.execute("""INSERT INTO pinecrest.care_actions (action_id, patient_id, encounter_id, action, note, approved_by)
               VALUES (%s, 'PC-01684', 'EN-005050', 'Schedule follow-up visit within 7 days', 'setup smoke test', 'setup-notebook')""",
            (test_id,))
show("SELECT action_id, patient_id, action, status, approved_by, approved_at FROM pinecrest.care_actions WHERE action_id = %s",
     (test_id,))
cur.execute("DELETE FROM pinecrest.care_actions WHERE action_id = %s", (test_id,))
print("deleted smoke-test row; writable table round-trip OK")
```
**output:**
```
action_id | patient_id | action | status | approved_by | approved_at
fc1a355a-1949-451d-b602-b20421351ac6 | PC-01684 | Schedule follow-up visit within 7 days | approved | setup-notebook | 2026-11-09 22:36:09.891621+00:00

deleted smoke-test row; writable table round-trip OK
```

### cell
```python
# Synced tables are refreshed from Unity Catalog; the app only gets SELECT on them (no write grants)
show("""SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS app_privileges
        FROM information_schema.role_table_grants WHERE grantee = %s GROUP BY 1 ORDER BY 1""", (APP_SP,))
```
**output:**
```
table_name | app_privileges
care_actions | INSERT, SELECT, UPDATE
pc_care_notes | SELECT
pc_risk_worklist | SELECT
```
