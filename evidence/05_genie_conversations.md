# Genie conversations — space `01f1dc8c44ba155391aaea55a2d641cc` (Pinecrest Readmission Insights)

Asked through the Genie Conversation API. Tables: pc_gold_readmission_risk, pc_gold_discharge_features, pc_gold_facility_readmissions.

## Q: How many high-risk patients does each facility have?

status: **COMPLETED** · conversation `01f1dc8c8d9e1cb18030195705f2f0c0` · message `01f1dc8c8dad1e68b1b994c67136db24`

Generated SQL:
```sql
SELECT `facility`, COUNT(*) AS `high_risk_patients`
FROM `users`.`narasimha_kamathardi`.`pc_gold_readmission_risk`
WHERE `facility` IS NOT NULL
  AND `risk_tier` IS NOT NULL
  AND `risk_tier` ILIKE '%High%'
GROUP BY `facility`
ORDER BY `high_risk_patients` DESC, `facility` ASC;
```

| facility | high_risk_patients |
|---|---|
| Pinecrest Main | 91 |
| Pinecrest North | 89 |
| Pinecrest Valley | 73 |

Genie answer:

> Each facility has the following number of **high-risk patients**:
> - **Pinecrest Main**: **91**
> - **Pinecrest North**: **89**
> - **Pinecrest Valley**: **73**
> Across the 3 facilities shown, **Pinecrest Main** has the most high-risk patients and **Pinecrest Valley** has the fewest.

## Q: Which high-risk patients have no follow-up visit scheduled? Show the top 5 by risk score.

status: **COMPLETED** · conversation `01f1dc8c98431ed4ad7f3ac822fd9f1c` · message `01f1dc8c985116069f823c9066ba6c87`

Generated SQL:
```sql
SELECT `patient_id`, `encounter_id`, `facility`, `primary_condition`, `discharge_date`, `risk_score`, `risk_tier`, `recommended_action`
FROM `users`.`narasimha_kamathardi`.`pc_gold_readmission_risk`
WHERE `risk_tier` ILIKE '%high%'
  AND `followup_scheduled` = false
  AND `risk_score` IS NOT NULL
ORDER BY `risk_score` DESC
LIMIT 5
```

| patient_id | encounter_id | facility | primary_condition | discharge_date | risk_score | risk_tier | recommended_action |
|---|---|---|---|---|---|---|---|
| PC-01684 | EN-005050 | Pinecrest Main | CHF | 2026-09-07 | 0.9119 | High | Schedule follow-up visit within 7 days |
| PC-00609 | EN-001830 | Pinecrest North | Sepsis | 2026-07-14 | 0.8885 | High | Schedule follow-up visit within 7 days |
| PC-00662 | EN-001981 | Pinecrest Main | AMI | 2026-08-07 | 0.8773 | High | Schedule follow-up visit within 7 days |
| PC-00549 | EN-001653 | Pinecrest Valley | COPD | 2026-03-20 | 0.8764 | High | Schedule follow-up visit within 7 days |
| PC-01287 | EN-003841 | Pinecrest Valley | Diabetes | 2026-09-11 | 0.8728 | High | Schedule follow-up visit within 7 days |

Genie answer:

> The top 5 **high-risk** patients with **no follow-up visit scheduled** are:
> - **PC-01684** at **Pinecrest Main** — risk score **0.9119**, condition **CHF**, discharged **2026-09-07**
> - **PC-00609** at **Pinecrest North** — risk score **0.8885**, condition **Sepsis**, discharged **2026-07-14**
> - **PC-00662** at **Pinecrest Main** — risk score **0.8773**, condition **AMI**, discharged **2026-08-07**
> - **PC-00549** at **Pinecrest Valley** — risk score **0.8764**, condition **COPD**, discharged **2026-03-20**
> - **PC-01287** at **Pinecrest Valley** — risk score **0.8728**, condition **Diabetes**, discharged **2026-09-11**
> 
> Across all 5 results, the recommended action is consistently **Schedule follow-up visit within 7 days**, and the highest risk score shown is **0.9119**.

## Q: Which facility had the highest overall readmission rate for COPD?

status: **COMPLETED** · conversation `01f1dc8ca54b101ebea5541da3f44d0f` · message `01f1dc8ca55f129791524b55872d35cf`

Generated SQL:
```sql
WITH facility_rates AS (
  SELECT
    `facility`,
    SUM(`readmissions`) AS `total_readmissions`,
    SUM(`discharges`) AS `total_discharges`,
    try_divide(SUM(`readmissions`) * 1.0,SUM(`discharges`)) AS `overall_readmission_rate`
  FROM `users`.`narasimha_kamathardi`.`pc_gold_facility_readmissions`
  WHERE `primary_condition` IS NOT NULL
    AND `facility` IS NOT NULL
    AND `primary_condition` ILIKE '%COPD%'
  GROUP BY `facility`
), ranked AS (
  SELECT
    `facility`,
    `total_readmissions`,
    `total_discharges`,
    `overall_readmission_rate`,
    RANK() OVER (ORDER BY `overall_readmission_rate` DESC) AS `facility_rank`
  FROM facility_rates
)
SELECT
  `facility`,
  `total_readmissions`,
  `total_discharges`,
  `overall_readmission_rate`
FROM ranked
WHERE `facility_rank` <= 1
```

| facility | total_readmissions | total_discharges | overall_readmission_rate |
|---|---|---|---|
| Pinecrest North | 58 | 279 | 0.2078853046594982 |

Genie answer:

> **Pinecrest North** had the highest overall COPD readmission rate, with **58** readmissions out of **279** discharges, for an overall readmission rate of **0.2079** (about **20.8%**). Since the result contains the top-ranked facility only, **Pinecrest North** is the highest facility shown for COPD readmissions.

## Q: What is the average predicted readmission risk by discharge disposition?

status: **COMPLETED** · conversation `01f1dc8cafff13b09a9e51810bc00304` · message `01f1dc8cb00e15b386399ef11b76d768`

Generated SQL:
```sql
SELECT `discharge_disposition`, AVG(`risk_score`) AS `avg_predicted_readmission_risk`, COUNT(*) AS `record_count`
FROM `users`.`narasimha_kamathardi`.`pc_gold_readmission_risk`
WHERE `discharge_disposition` IS NOT NULL
  AND `risk_score` IS NOT NULL
GROUP BY `discharge_disposition`
ORDER BY `avg_predicted_readmission_risk` DESC
```

| discharge_disposition | avg_predicted_readmission_risk | record_count |
|---|---|---|
| Left AMA | 0.29235212765957447 | 94 |
| Skilled nursing | 0.16806327160493828 | 324 |
| Home health | 0.13669039665970775 | 479 |
| Home | 0.13445022665457845 | 1103 |

Genie answer:

> The average predicted readmission risk is highest for **Left AMA** at **0.292** across **94** records, followed by **Skilled nursing** at **0.168** (**324** records), **Home health** at **0.137** (**479** records), and **Home** at **0.134** (**1,103** records). Across these **4 discharge dispositions**, patients discharged **Left AMA** show a notably higher average predicted readmission risk than the other groups.

