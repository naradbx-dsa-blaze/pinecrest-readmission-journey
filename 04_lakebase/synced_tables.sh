#!/usr/bin/env bash
# Lakebase instance, its Unity Catalog database catalog, and the UC -> Postgres synced tables.
set -euo pipefail
P="--profile fe-east"

databricks database create-database-instance pinecrest-lakebase --capacity CU_1 $P
databricks database create-database-catalog pinecrest_lakebase pinecrest-lakebase databricks_postgres \
  --create-database-if-not-exists $P

# ML risk worklist: incremental (TRIGGERED) via Change Data Feed on the source table
databricks database create-synced-database-table $P --json '{
  "name": "pinecrest_lakebase.public.pc_risk_worklist",
  "spec": {"source_table_full_name": "users.narasimha_kamathardi.pc_gold_readmission_risk",
           "primary_key_columns": ["patient_id"], "scheduling_policy": "TRIGGERED"}}'

# coordinator notes: SNAPSHOT copy of the Lakeflow silver streaming table
databricks database create-synced-database-table $P --json '{
  "name": "pinecrest_lakebase.public.pc_care_notes",
  "spec": {"source_table_full_name": "users.narasimha_kamathardi.pc_silver_care_notes",
           "primary_key_columns": ["note_id"], "scheduling_policy": "SNAPSHOT"}}'

databricks database get-synced-database-table pinecrest_lakebase.public.pc_risk_worklist $P
databricks database get-synced-database-table pinecrest_lakebase.public.pc_care_notes $P
