# Databricks notebook source
# Read back the care actions the app's coordinators approved, straight from Lakebase, and join
# them to the ML risk worklist they came from — the closed loop UC -> Lakebase -> app -> Lakebase.

# COMMAND ----------

# MAGIC %pip install -q "psycopg[binary]==3.2.3" "databricks-sdk>=0.60.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import uuid

import psycopg
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
inst = w.database.get_database_instance("pinecrest-lakebase")
token = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[inst.name]).token
cur = psycopg.connect(host=inst.read_write_dns, dbname="databricks_postgres", user=w.current_user.me().user_name,
                      password=token, sslmode="require", autocommit=True).cursor()

cur.execute("""
    SELECT a.action_id, a.patient_id, w.risk_score, w.risk_tier, w.recommended_action, a.action,
           a.status, a.approved_by, a.approved_at
    FROM pinecrest.care_actions a JOIN public.pc_risk_worklist w USING (patient_id)
    ORDER BY a.approved_at DESC""")
print(" | ".join(d.name for d in cur.description))
for r in cur.fetchall():
    print(" | ".join(str(v) for v in r))
