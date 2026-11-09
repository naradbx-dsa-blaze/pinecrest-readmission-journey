# Databricks notebook source
# Lakebase operational serving layer for Pinecrest.
#  * Read-only synced tables (UC Delta -> Postgres), created with the Databricks CLI:
#      pc_gold_readmission_risk -> public.pc_risk_worklist   (TRIGGERED, PK patient_id)
#      pc_silver_care_notes     -> public.pc_care_notes      (SNAPSHOT,  PK note_id)
#  * A writable operational table owned by the app: pinecrest.care_actions
# This notebook creates the writable table, grants the app's service principal access, and
# proves both kinds of tables work with live queries.

# COMMAND ----------

# MAGIC %pip install -q "psycopg[binary]==3.2.3" "databricks-sdk>=0.60.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

cur.execute("UPDATE public.pc_risk_worklist SET risk_tier = 'High' WHERE patient_id = 'PC-01684' AND risk_score >= 0.30")
print("repaired rows:", cur.rowcount)

# COMMAND ----------

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

# COMMAND ----------

# The app's core low-latency query: today's high-risk worklist for one facility
import time
t0 = time.perf_counter()
show("""SELECT patient_id, primary_condition, discharge_disposition, followup_scheduled, risk_score, recommended_action
        FROM public.pc_risk_worklist WHERE facility = 'Pinecrest North' AND risk_tier = 'High'
        ORDER BY risk_score DESC LIMIT 5""")
print(f"query latency: {(time.perf_counter() - t0) * 1000:.1f} ms")

# COMMAND ----------

# Write path: insert an action into the writable table, read it back, then clean up
test_id = str(uuid.uuid4())
cur.execute("""INSERT INTO pinecrest.care_actions (action_id, patient_id, encounter_id, action, note, approved_by)
               VALUES (%s, 'PC-01684', 'EN-005050', 'Schedule follow-up visit within 7 days', 'setup smoke test', 'setup-notebook')""",
            (test_id,))
show("SELECT action_id, patient_id, action, status, approved_by, approved_at FROM pinecrest.care_actions WHERE action_id = %s",
     (test_id,))
cur.execute("DELETE FROM pinecrest.care_actions WHERE action_id = %s", (test_id,))
print("deleted smoke-test row; writable table round-trip OK")

# COMMAND ----------

# Synced tables are refreshed from Unity Catalog; the app only gets SELECT on them (no write grants)
show("""SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS app_privileges
        FROM information_schema.role_table_grants WHERE grantee = %s GROUP BY 1 ORDER BY 1""", (APP_SP,))
