# Lakeflow pipeline output (pipeline pinecrest-readmission-ingest, id 385fd863-e585-4340-bded-f54d2d6d615c)

Executed 2026-11-09 22:11 UTC on warehouse `148ccb90800933a1` (fe-east) via the SQL Statement API.

```sql
SELECT 'bronze' layer, 'pc_bronze_patients' tbl, count(*) n FROM pc_bronze_patients UNION ALL SELECT 'bronze','pc_bronze_encounters',count(*) FROM pc_bronze_encounters UNION ALL SELECT 'bronze','pc_bronze_care_notes',count(*) FROM pc_bronze_care_notes UNION ALL SELECT 'silver','pc_silver_patients',count(*) FROM pc_silver_patients UNION ALL SELECT 'silver','pc_silver_encounters',count(*) FROM pc_silver_encounters UNION ALL SELECT 'silver','pc_silver_care_notes',count(*) FROM pc_silver_care_notes UNION ALL SELECT 'gold','pc_gold_discharge_features',count(*) FROM pc_gold_discharge_features UNION ALL SELECT 'gold','pc_gold_facility_readmissions',count(*) FROM pc_gold_facility_readmissions
```

| layer | tbl | n |
|---|---|---|
| bronze | pc_bronze_patients | 2000 |
| bronze | pc_bronze_encounters | 6038 |
| bronze | pc_bronze_care_notes | 3000 |
| silver | pc_silver_patients | 2000 |
| silver | pc_silver_encounters | 6013 |
| silver | pc_silver_care_notes | 3000 |
| gold | pc_gold_discharge_features | 6013 |
| gold | pc_gold_facility_readmissions | 190 |

(8 rows)

```sql
SELECT origin.flow_name, details:flow_progress.data_quality.dropped_records AS dropped_records, details:flow_progress.data_quality.expectations AS expectations FROM event_log(TABLE(pc_silver_encounters)) WHERE event_type = 'flow_progress' AND origin.flow_name LIKE '%silver%' AND details:flow_progress.data_quality.expectations IS NOT NULL ORDER BY timestamp DESC
```

| flow_name | dropped_records | expectations |
|---|---|---|
| users.narasimha_kamathardi.pc_silver_patients | 0 | [{"name":"valid_patient_id","dataset":"users.narasimha_kamathardi.pc_silver_patients","passed_records":2000,"failed_records":0}] |
| users.narasimha_kamathardi.pc_silver_care_notes | 0 | [{"name":"has_text","dataset":"users.narasimha_kamathardi.pc_silver_care_notes","passed_records":3000,"failed_records":0}] |
| users.narasimha_kamathardi.pc_silver_encounters | 25 | [{"name":"valid_dates","dataset":"users.narasimha_kamathardi.pc_silver_encounters","passed_records":6038,"failed_records":0},{"name":"valid_length_of_stay","dataset":"users.narasimha_kamathardi.pc_silver_encounters","passed_records":6013,"failed_records":25}] |

(3 rows)

```sql
SELECT origin.update_id, event_type, message, timestamp FROM event_log(TABLE(pc_silver_encounters)) WHERE event_type IN ('create_update','update_progress') ORDER BY timestamp
```

| update_id | event_type | message | timestamp |
|---|---|---|---|
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | create_update | Update 09aa97 started by API_CALL. | 2026-11-09T17:09:10.187-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is WAITING_FOR_RESOURCES. | 2026-11-09T17:09:12.792-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is INITIALIZING. | 2026-11-09T17:09:24.082-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is RESETTING. | 2026-11-09T17:09:46.139-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is SETTING_UP_TABLES. | 2026-11-09T17:09:46.184-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is RUNNING. | 2026-11-09T17:09:55.376-05:00 |
| 09aa97e4-c57f-4b64-be6e-cc9ecbaa47c9 | update_progress | Update 09aa97 is COMPLETED. | 2026-11-09T17:10:22.989-05:00 |

(7 rows)

```sql
SELECT * FROM pc_gold_facility_readmissions ORDER BY readmission_rate DESC LIMIT 10
```

| facility | primary_condition | discharge_month | discharges | readmissions | readmission_rate |
|---|---|---|---|---|---|
| Pinecrest North | COPD | 2026-04-30T20:00:00.000-04:00 | 28 | 11 | 0.3929 |
| Pinecrest Main | AMI | 2026-08-31T20:00:00.000-04:00 | 21 | 7 | 0.3333 |
| Pinecrest Main | COPD | 2025-12-31T19:00:00.000-05:00 | 25 | 8 | 0.32 |
| Pinecrest Main | COPD | 2026-03-31T20:00:00.000-04:00 | 23 | 7 | 0.3043 |
| Pinecrest North | Hip fracture | 2026-02-28T19:00:00.000-05:00 | 27 | 8 | 0.2963 |
| Pinecrest Valley | CHF | 2026-05-31T20:00:00.000-04:00 | 32 | 9 | 0.2813 |
| Pinecrest Main | AMI | 2025-12-31T19:00:00.000-05:00 | 32 | 9 | 0.2813 |
| Pinecrest North | Pneumonia | 2026-03-31T20:00:00.000-04:00 | 37 | 10 | 0.2703 |
| Pinecrest Valley | CHF | 2026-08-31T20:00:00.000-04:00 | 27 | 7 | 0.2593 |
| Pinecrest Valley | CHF | 2026-06-30T20:00:00.000-04:00 | 35 | 9 | 0.2571 |

(10 rows)

