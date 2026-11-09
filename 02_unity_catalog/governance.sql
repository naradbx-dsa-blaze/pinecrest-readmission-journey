-- Unity Catalog governance for the Pinecrest readmission journey.
USE users.narasimha_kamathardi;

-- 1. Classify PHI columns with governed tags
ALTER TABLE pc_silver_patients ALTER COLUMN full_name SET TAGS ('phi' = 'name');
ALTER TABLE pc_silver_patients ALTER COLUMN phone     SET TAGS ('phi' = 'contact');
ALTER TABLE pc_silver_patients ALTER COLUMN zip_code  SET TAGS ('phi' = 'geo');
ALTER TABLE pc_gold_readmission_risk SET TAGS ('domain' = 'clinical', 'data_class' = 'amber');

-- 2. Mask PHI for anyone outside the care team (function-based column mask)
CREATE OR REPLACE FUNCTION pc_mask_phi(v STRING)
  RETURN CASE WHEN is_account_group_member('pinecrest_care_team') OR current_user() = 'narasimha.kamathardi@databricks.com'
              THEN v ELSE '***MASKED***' END;
ALTER TABLE pc_silver_patients ALTER COLUMN full_name SET MASK pc_mask_phi;
ALTER TABLE pc_silver_patients ALTER COLUMN phone     SET MASK pc_mask_phi;

-- 3. Document the business meaning (also improves Genie answers)
COMMENT ON TABLE pc_gold_readmission_risk IS
  'Latest discharge per patient scored by the pc_readmission_risk_model (champion). Drives the care-coordinator worklist.';
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN risk_score COMMENT 'Predicted probability of readmission within 30 days (0-1)';
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN risk_tier COMMENT 'High >= 0.30, Medium 0.15-0.30, Low < 0.15';
ALTER TABLE pc_gold_readmission_risk ALTER COLUMN recommended_action COMMENT 'Next-best outreach action for the care coordinator';

-- 4. Verify: tags, masks and comments as recorded in Unity Catalog
SELECT table_name, column_name, tag_name, tag_value FROM information_schema.column_tags
WHERE schema_name = 'narasimha_kamathardi' AND table_name LIKE 'pc_%' ORDER BY 1, 2;
SELECT table_name, tag_name, tag_value FROM information_schema.table_tags
WHERE schema_name = 'narasimha_kamathardi' AND table_name LIKE 'pc_%';
SELECT table_name, column_name, mask_name FROM information_schema.column_masks
WHERE table_schema = 'narasimha_kamathardi' AND table_name LIKE 'pc_%';
-- the mask in action: the owner sees real values; the same function returns ***MASKED*** for others
SELECT patient_id, full_name, phone FROM pc_silver_patients LIMIT 3;
SELECT pc_mask_phi('Ava Rivera') AS as_owner;
-- lineage: Unity Catalog captured raw volume -> bronze -> silver -> gold -> ML-scored table
SELECT DISTINCT source_table_full_name, target_table_full_name FROM system.access.table_lineage
WHERE target_table_full_name LIKE 'users.narasimha_kamathardi.pc_%' AND source_table_full_name IS NOT NULL ORDER BY 2;
