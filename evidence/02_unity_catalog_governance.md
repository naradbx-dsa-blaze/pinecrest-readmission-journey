# Unity Catalog governance applied + verified

Executed 2026-11-09 22:22 UTC on warehouse `148ccb90800933a1` (fe-east) via the SQL Statement API.

```sql
USE users.narasimha_kamathardi
```

OK

```sql
-- 1. Classify PHI columns with governed tags
ALTER TABLE pc_silver_patients ALTER COLUMN full_name SET TAGS ('phi' = 'name')
```

OK

```sql
ALTER TABLE pc_silver_patients ALTER COLUMN phone     SET TAGS ('phi' = 'contact')
```

OK

```sql
ALTER TABLE pc_silver_patients ALTER COLUMN zip_code  SET TAGS ('phi' = 'geo')
```

OK

```sql
ALTER TABLE pc_gold_readmission_risk SET TAGS ('domain' = 'clinical', 'data_class' = 'amber')
```

OK

```sql
-- 2. Mask PHI for anyone outside the care team (function-based column mask)
CREATE OR REPLACE FUNCTION pc_mask_phi(v STRING)
  RETURN CASE WHEN is_account_group_member('pinecrest_care_team') OR current_user() = 'narasimha.kamathardi@databricks.com'
              THEN v ELSE '***MASKED***' END
```

OK

```sql
ALTER TABLE pc_silver_patients ALTER COLUMN full_name SET MASK pc_mask_phi
```

OK

```sql
ALTER TABLE pc_silver_patients ALTER COLUMN phone     SET MASK pc_mask_phi
```

OK

```sql
-- 3. Document the business meaning (also improves Genie answers)
COMMENT ON TABLE pc_gold_readmission_risk IS
  'Latest discharge per patient scored by the pc_readmission_risk_model (champion). Drives the care-coordinator worklist.'
```

OK

```sql
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN risk_score COMMENT 'Predicted probability of readmission within 30 days (0-1)'
```

OK

```sql
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN risk_tier COMMENT 'High >= 0.30, Medium 0.15-0.30, Low < 0.15'
```

OK

```sql
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN recommended_action COMMENT 'Next-best outreach action for the care coordinator'
```

OK

```sql
-- 4. Verify: tags, masks and comments as recorded in Unity Catalog
SELECT table_name, column_name, tag_name, tag_value FROM information_schema.column_tags
WHERE schema_name = 'narasimha_kamathardi' AND table_name LIKE 'pc_%' ORDER BY 1, 2
```

| table_name | column_name | tag_name | tag_value |
|---|---|---|---|
| pc_silver_patients | full_name | phi | name |
| pc_silver_patients | phone | phi | contact |
| pc_silver_patients | zip_code | phi | geo |

(3 rows)

```sql
SELECT table_name, tag_name, tag_value FROM information_schema.table_tags
WHERE schema_name = 'narasimha_kamathardi' AND table_name LIKE 'pc_%'
```

| table_name | tag_name | tag_value |
|---|---|---|
| pc_gold_readmission_risk | data_class | amber |
| pc_gold_readmission_risk | domain | clinical |

(2 rows)

```sql
SELECT table_name, column_name, mask_name FROM information_schema.column_masks
WHERE table_schema = 'narasimha_kamathardi' AND table_name LIKE 'pc_%'
```

| table_name | column_name | mask_name |
|---|---|---|
| pc_silver_patients | phone | users.narasimha_kamathardi.pc_mask_phi |
| pc_silver_patients | full_name | users.narasimha_kamathardi.pc_mask_phi |

(2 rows)

```sql
SELECT patient_id, full_name, phone FROM pc_silver_patients LIMIT 3
```

| patient_id | full_name | phone |
|---|---|---|
| PC-00001 | Mateo Chen | 555-656-8462 |
| PC-00002 | Owen Silva | 555-675-6346 |
| PC-00003 | Raj Patel | 555-520-3203 |

(3 rows)

```sql
SELECT pc_mask_phi('Ava Rivera') AS as_owner
```

| as_owner |
|---|
| Ava Rivera |

(1 rows)

```sql
SELECT DISTINCT source_table_full_name, target_table_full_name FROM system.access.table_lineage
WHERE target_table_full_name LIKE 'users.narasimha_kamathardi.pc_%' AND source_table_full_name IS NOT NULL ORDER BY 2
```

| source_table_full_name | target_table_full_name |
|---|---|
| users.narasimha_kamathardi.pc_silver_patients | users.narasimha_kamathardi.pc_gold_discharge_features |
| users.narasimha_kamathardi.pc_silver_encounters | users.narasimha_kamathardi.pc_gold_discharge_features |
| users.narasimha_kamathardi.pc_silver_encounters | users.narasimha_kamathardi.pc_gold_facility_readmissions |
| users.narasimha_kamathardi.pc_bronze_care_notes | users.narasimha_kamathardi.pc_silver_care_notes |
| users.narasimha_kamathardi.pc_bronze_encounters | users.narasimha_kamathardi.pc_silver_encounters |
| users.narasimha_kamathardi.pc_bronze_patients | users.narasimha_kamathardi.pc_silver_patients |

(6 rows)

