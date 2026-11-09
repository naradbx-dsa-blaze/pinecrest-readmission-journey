-- Lakeflow Spark Declarative Pipeline: raw files in a UC volume -> bronze -> silver -> gold.
-- Target: users.narasimha_kamathardi (all tables prefixed pc_). Serverless.

-- ---------------- Bronze: incremental ingest of raw files (Auto Loader) ----------------
CREATE OR REFRESH STREAMING TABLE pc_bronze_patients
COMMENT 'Raw patient roster ingested from /Volumes/.../pinecrest_raw/patients'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/users/narasimha_kamathardi/pinecrest_raw/patients', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE pc_bronze_encounters
COMMENT 'Raw inpatient discharges ingested from /Volumes/.../pinecrest_raw/encounters'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/users/narasimha_kamathardi/pinecrest_raw/encounters', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE pc_bronze_care_notes
COMMENT 'Raw care-coordinator notes (JSON lines)'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/users/narasimha_kamathardi/pinecrest_raw/care_notes', format => 'json');

-- ---------------- Silver: typed, validated ----------------
CREATE OR REFRESH STREAMING TABLE pc_silver_patients (
  CONSTRAINT valid_patient_id EXPECT (patient_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Cleaned patient roster'
AS SELECT patient_id, full_name, phone, CAST(age AS INT) AS age, sex, zip_code, payer,
          CAST(chronic_conditions AS INT) AS chronic_conditions
FROM STREAM(pc_bronze_patients);

CREATE OR REFRESH STREAMING TABLE pc_silver_encounters (
  CONSTRAINT valid_length_of_stay EXPECT (length_of_stay > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_dates EXPECT (discharge_date >= admit_date) ON VIOLATION DROP ROW
)
COMMENT 'Cleaned inpatient discharges; rows with invalid length of stay are dropped'
AS SELECT encounter_id, patient_id, facility, primary_condition,
          CAST(admit_date AS DATE) AS admit_date, CAST(discharge_date AS DATE) AS discharge_date,
          CAST(length_of_stay AS INT) AS length_of_stay, discharge_disposition,
          CAST(prior_admissions_12m AS INT) AS prior_admissions_12m,
          CAST(followup_scheduled AS BOOLEAN) AS followup_scheduled,
          CAST(readmitted_30d AS BOOLEAN) AS readmitted_30d
FROM STREAM(pc_bronze_encounters);

CREATE OR REFRESH STREAMING TABLE pc_silver_care_notes (
  CONSTRAINT has_text EXPECT (note_text IS NOT NULL AND length(note_text) > 0) ON VIOLATION DROP ROW
)
COMMENT 'Cleaned care-coordinator notes'
AS SELECT note_id, encounter_id, patient_id, CAST(note_date AS DATE) AS note_date, note_text
FROM STREAM(pc_bronze_care_notes);

-- ---------------- Gold: model-ready + business views ----------------
CREATE OR REFRESH MATERIALIZED VIEW pc_gold_discharge_features
COMMENT 'One row per discharge with patient features + readmission label (ML training set)'
AS SELECT e.encounter_id, e.patient_id, e.facility, e.primary_condition, e.discharge_date,
          e.length_of_stay, e.discharge_disposition, e.prior_admissions_12m, e.followup_scheduled,
          p.age, p.sex, p.payer, p.chronic_conditions, e.readmitted_30d
FROM pc_silver_encounters e JOIN pc_silver_patients p USING (patient_id);

CREATE OR REFRESH MATERIALIZED VIEW pc_gold_facility_readmissions
COMMENT 'Monthly 30-day readmission rate by facility and condition (for Genie / exec reporting)'
AS SELECT facility, primary_condition, date_trunc('MONTH', discharge_date) AS discharge_month,
          count(*) AS discharges, sum(CAST(readmitted_30d AS INT)) AS readmissions,
          round(avg(CAST(readmitted_30d AS INT)), 4) AS readmission_rate
FROM pc_silver_encounters GROUP BY ALL;
