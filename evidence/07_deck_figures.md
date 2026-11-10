# Figures used in the deck charts

Executed 2026-11-10 02:34 UTC on warehouse `148ccb90800933a1` (fe-east) via the SQL Statement API.

```sql
SELECT round(100*avg(CAST(readmitted_30d AS INT)),1) AS overall_readmit_pct, count(*) AS discharges FROM pc_gold_discharge_features
```

| overall_readmit_pct | discharges |
|---|---|
| 14.7 | 6013 |

(1 rows)

```sql
SELECT r.risk_tier, count(*) AS patients, round(100*avg(CAST(f.readmitted_30d AS INT)),1) AS actual_readmit_pct, round(100*avg(r.risk_score),1) AS avg_predicted_pct FROM pc_gold_readmission_risk r JOIN pc_gold_discharge_features f USING (encounter_id) GROUP BY 1 ORDER BY 3 DESC
```

| risk_tier | patients | actual_readmit_pct | avg_predicted_pct |
|---|---|---|---|
| High | 253 | 51.0 | 48.4 |
| Medium | 375 | 21.9 | 21.3 |
| Low | 1372 | 5.8 | 6.8 |

(3 rows)

```sql
SELECT discharge_disposition, count(*) AS discharges, round(100*avg(CAST(readmitted_30d AS INT)),1) AS readmit_pct FROM pc_gold_discharge_features GROUP BY 1 ORDER BY 3 DESC
```

| discharge_disposition | discharges | readmit_pct |
|---|---|---|
| Left AMA | 279 | 26.2 |
| Skilled nursing | 907 | 18.1 |
| Home health | 1533 | 13.4 |
| Home | 3294 | 13.4 |

(4 rows)

```sql
SELECT followup_scheduled, count(*) AS discharges, round(100*avg(CAST(readmitted_30d AS INT)),1) AS readmit_pct FROM pc_gold_discharge_features GROUP BY 1
```

| followup_scheduled | discharges | readmit_pct |
|---|---|---|
| true | 3689 | 11.8 |
| false | 2324 | 19.2 |

(2 rows)

```sql
SELECT primary_condition, count(*) AS discharges, round(100*avg(CAST(readmitted_30d AS INT)),1) AS readmit_pct FROM pc_gold_discharge_features GROUP BY 1 ORDER BY 3 DESC
```

| primary_condition | discharges | readmit_pct |
|---|---|---|
| COPD | 831 | 17.6 |
| CHF | 862 | 17.4 |
| Diabetes | 849 | 14.3 |
| AMI | 855 | 13.8 |
| Sepsis | 876 | 13.7 |
| Hip fracture | 893 | 13.3 |
| Pneumonia | 847 | 12.8 |

(7 rows)

