# Databricks App execution — pinecrest-care-coordinator

URL: https://pinecrest-care-coordinator-984752964297111.11.azure.databricksapps.com (Streamlit, source in `06_app/`)

## 1. Deployment (`databricks apps get`)
```json
{
 "name": "pinecrest-care-coordinator",
 "url": "https://pinecrest-care-coordinator-984752964297111.11.azure.databricksapps.com",
 "app_status": {
  "message": "App has status: App is running",
  "state": "RUNNING"
 },
 "compute_status": {
  "message": "App compute is running.",
  "state": "ACTIVE"
 },
 "active_deployment": {
  "create_time": "2026-11-09T22:44:48Z",
  "creator": "narasimha.kamathardi@databricks.com",
  "deployment_artifacts": {
   "source_code_path": "/Workspace/Users/ca18f7c1-92c2-41cb-9554-82eebcd35981/src/01f1dc8f2aef198da493860d5a827c99"
  },
  "deployment_id": "01f1dc8f2aef198da493860d5a827c99",
  "mode": "SNAPSHOT",
  "source_code_path": "/Workspace/Users/narasimha.kamathardi@databricks.com/pinecrest-readmission-journey/06_app",
  "status": {
   "message": "App started successfully",
   "state": "SUCCEEDED"
  },
  "update_time": "2026-11-09T22:44:56Z"
 },
 "resources": [
  {
   "database": {
    "database_name": "databricks_postgres",
    "instance_name": "pinecrest-lakebase",
    "permission": "CAN_CONNECT_AND_CREATE"
   },
   "name": "database"
  },
  {
   "name": "llm",
   "serving_endpoint": {
    "name": "databricks-claude-sonnet-5-5",
    "permission": "CAN_QUERY"
   }
  }
 ]
}
```

## 2. App log — a coordinator using it (`databricks apps logs`)

Worklist reads come from Lakebase; the explanation comes from the Claude serving endpoint; the approval writes to the writable Lakebase table.
```
2026-11-09T22:43:28Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:44:04Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:44:10Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:45:34Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:45:46Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:45:49Z [APP] [explain] patient=PC-01684 endpoint=databricks-claude-sonnet-5-5 notes=2 response="- **Why high risk:** This CHF patient has a very high readmission risk score (0.9119, High tier) and was discharged on 2026-09-07 to skilled nursing with **no follow-up visit scheduled**, which leaves a gap in post-discharge monitoring.\n\n- **Barriers to follow-up:** Per the notes, transportation to a follow-up visit isn't arranged yet (per the daughter), and the patient reports that the cost of the inhaler and copays is a barrier. Both could lead to missed care or missed medications.\n\n- **First action:** Schedule the follow-up visit within 7 days (the recommended action), and book it together with transportation. Coordinate with the daughter and the skilled nursing facility, and flag the cost concerns for financial or medication assistance support so the visit and treatment are actually achievable."
2026-11-09T22:45:55Z [APP] [worklist] facility=None tier=High rows=200 source=lakebase:public.pc_risk_worklist
2026-11-09T22:45:56Z [APP] [approve] action_id=c3c92782-cca5-4164-92db-dec741e8fd2d patient=PC-01684 action='Schedule follow-up visit within 7 days' by=narasimha.kamathardi@databricks.com -> lakebase:pinecrest.care_actions
```

## 3. The approved action read back from Lakebase

Serverless job run `32713408178944` running `04_lakebase/verify_app_writeback.py` — `pinecrest.care_actions` joined to the synced ML worklist:
```
action_id | patient_id | risk_score | risk_tier | recommended_action | action | status | approved_by | approved_at
c3c92782-cca5-4164-92db-dec741e8fd2d | PC-01684 | 0.9119 | High | Schedule follow-up visit within 7 days | Schedule follow-up visit within 7 days | approved | narasimha.kamathardi@databricks.com | 2026-11-09 22:45:56.328267+00:00
```
