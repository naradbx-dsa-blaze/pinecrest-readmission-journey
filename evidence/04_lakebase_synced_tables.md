# Lakebase synced tables — live status

Captured 2026-11-09 22:38 UTC with `databricks database get-synced-database-table`.

## pinecrest_lakebase.public.pc_risk_worklist
```json
{
 "name": "pinecrest_lakebase.public.pc_risk_worklist",
 "spec": {
  "primary_key_columns": [
   "patient_id"
  ],
  "scheduling_policy": "TRIGGERED",
  "source_table_full_name": "users.narasimha_kamathardi.pc_gold_readmission_risk"
 },
 "data_synchronization_status": {
  "detailed_state": "SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE",
  "last_sync": {
   "delta_table_sync_info": {
    "delta_commit_timestamp": "2026-11-09T22:22:41Z",
    "delta_commit_version": 13
   },
   "sync_end_timestamp": "2026-11-09T22:23:46.395898Z",
   "sync_start_timestamp": "2026-11-09T22:23:35.185837Z"
  },
  "message": "Synced table creation succeeded using Delta Live Tables: https://adb-984752964297111.11.azuredatabricks.net#joblist/pipelines/aa0c81ce-d09b-4bea-92d4-1c2994b26efa/updates/8ba1d586-00db-457c-91f1-e3401b7e786c.",
  "pipeline_id": "aa0c81ce-d09b-4bea-92d4-1c2994b26efa",
  "triggered_update_status": {
   "last_processed_commit_version": 13,
   "timestamp": "2026-11-09T22:23:46Z"
  }
 },
 "database_instance_name": null,
 "logical_database_name": null
}
```

## pinecrest_lakebase.public.pc_care_notes
```json
{
 "name": "pinecrest_lakebase.public.pc_care_notes",
 "spec": {
  "primary_key_columns": [
   "note_id"
  ],
  "scheduling_policy": "SNAPSHOT",
  "source_table_full_name": "users.narasimha_kamathardi.pc_silver_care_notes"
 },
 "data_synchronization_status": {
  "detailed_state": "SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE",
  "last_sync": {
   "delta_table_sync_info": {
    "delta_commit_timestamp": "2026-11-09T22:10:13Z",
    "delta_commit_version": 2
   },
   "sync_end_timestamp": "2026-11-09T22:18:16.982517Z",
   "sync_start_timestamp": "2026-11-09T22:18:04.638832Z"
  },
  "message": "Synced table creation succeeded using Delta Live Tables: https://adb-984752964297111.11.azuredatabricks.net#joblist/pipelines/73f4f8e1-c760-4f62-a1f8-d0a9d60f50d9/updates/3e433171-af6c-4cb0-8060-ada8923f6e95.",
  "pipeline_id": "73f4f8e1-c760-4f62-a1f8-d0a9d60f50d9",
  "triggered_update_status": {
   "last_processed_commit_version": 2,
   "timestamp": "2026-11-09T22:18:16Z"
  }
 },
 "database_instance_name": null,
 "logical_database_name": null
}
```
