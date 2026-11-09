"""Generate the synthetic raw dataset for Pinecrest Health (fictional hospital system).

All people, names and records are synthetic. Output lands in ./raw/ and is uploaded to
the UC volume /Volumes/users/narasimha_kamathardi/pinecrest_raw/ for Lakeflow ingestion.

    python3 data_gen/generate.py
"""
import json
import os

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUT, exist_ok=True)

N_PATIENTS = 2000
FIRST = ["Ava", "Liam", "Mia", "Noah", "Zoe", "Eli", "Ivy", "Owen", "Ruby", "Jack", "Nora", "Leo",
         "Lena", "Omar", "Priya", "Raj", "Sofia", "Mateo", "Hana", "Kai"]
LAST = ["Rivera", "Chen", "Patel", "Okafor", "Novak", "Haddad", "Larsen", "Moreau", "Silva", "Kim",
        "Brooks", "Dubois", "Nakamura", "Ibrahim", "Kowalski", "Reyes", "Singh", "Muller"]
PAYERS = ["Medicare", "Medicaid", "Commercial", "Self-pay"]
CONDITIONS = ["CHF", "COPD", "Diabetes", "Pneumonia", "AMI", "Sepsis", "Hip fracture"]
DISPOSITIONS = ["Home", "Home health", "Skilled nursing", "Left AMA"]
FACILITIES = ["Pinecrest Main", "Pinecrest North", "Pinecrest Valley"]

# ---- patients -------------------------------------------------------------------------
age = rng.integers(25, 95, N_PATIENTS)
patients = pd.DataFrame({
    "patient_id": [f"PC-{i:05d}" for i in range(1, N_PATIENTS + 1)],
    "full_name": [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(N_PATIENTS)],
    "phone": [f"555-{rng.integers(100, 999)}-{rng.integers(1000, 9999)}" for _ in range(N_PATIENTS)],
    "age": age,
    "sex": rng.choice(["F", "M"], N_PATIENTS),
    "zip_code": rng.choice(["30301", "30305", "30309", "30318", "30324", "30331"], N_PATIENTS),
    "payer": rng.choice(PAYERS, N_PATIENTS, p=[0.45, 0.2, 0.3, 0.05]),
    "chronic_conditions": np.clip(rng.poisson(1 + (age - 25) / 30), 0, 8),
})

# ---- encounters (inpatient discharges) ------------------------------------------------
rows = []
enc = 0
for p in patients.itertuples():
    for _ in range(rng.integers(1, 6)):
        enc += 1
        los = int(np.clip(rng.gamma(2.0, 2.2), 1, 30))
        admit = pd.Timestamp("2026-01-01") + pd.Timedelta(days=int(rng.integers(0, 260)))
        dispo = rng.choice(DISPOSITIONS, p=[0.55, 0.25, 0.15, 0.05])
        followup = bool(rng.random() < 0.6)
        prior = int(rng.poisson(0.4 + p.chronic_conditions * 0.25))
        cond = rng.choice(CONDITIONS)
        # ground-truth readmission risk (what the ML model has to learn)
        logit = (-3.2 + 0.025 * (p.age - 60) + 0.30 * p.chronic_conditions + 0.35 * prior
                 + 0.06 * los + (0.9 if dispo == "Left AMA" else 0) + (0.4 if dispo == "Skilled nursing" else 0)
                 - (0.8 if followup else 0) + (0.5 if cond in ("CHF", "COPD") else 0)
                 + (0.3 if p.payer == "Medicaid" else 0))
        readmit = bool(rng.random() < 1 / (1 + np.exp(-logit)))
        rows.append({
            "encounter_id": f"EN-{enc:06d}", "patient_id": p.patient_id,
            "facility": rng.choice(FACILITIES), "primary_condition": cond,
            "admit_date": admit.date().isoformat(),
            "discharge_date": (admit + pd.Timedelta(days=los)).date().isoformat(),
            "length_of_stay": los, "discharge_disposition": dispo,
            "prior_admissions_12m": prior, "followup_scheduled": followup,
            "readmitted_30d": readmit,
        })
encounters = pd.DataFrame(rows)

# a few dirty rows so the pipeline's quality expectations have something to catch
dirty = encounters.sample(25, random_state=1).copy()
dirty["length_of_stay"] = -1
dirty["encounter_id"] = [f"EN-BAD{i:03d}" for i in range(len(dirty))]
encounters = pd.concat([encounters, dirty], ignore_index=True)

# ---- coordinator notes (unstructured, for GenAI) --------------------------------------
TEMPLATES = [
    "Patient lives alone and reports difficulty getting to the pharmacy for {cond} medications.",
    "Spoke with daughter; transportation to follow-up visit is not arranged yet.",
    "Patient confused about new {cond} medication schedule at discharge.",
    "Home health visit completed, vitals stable, patient engaged with care plan.",
    "Missed two calls; voicemail left about follow-up appointment.",
    "Patient states cost of inhaler and copays is a barrier.",
    "Caregiver requested help scheduling cardiology follow-up.",
    "Patient doing well, walking daily, no new symptoms reported.",
]
notes = []
for e in encounters[encounters["length_of_stay"] > 0].sample(3000, random_state=7).itertuples():
    notes.append({
        "note_id": f"NT-{len(notes) + 1:06d}", "encounter_id": e.encounter_id,
        "patient_id": e.patient_id, "note_date": e.discharge_date,
        "note_text": rng.choice(TEMPLATES).format(cond=e.primary_condition),
    })

patients.to_csv(os.path.join(OUT, "patients.csv"), index=False)
encounters.to_csv(os.path.join(OUT, "encounters.csv"), index=False)
with open(os.path.join(OUT, "care_notes.jsonl"), "w") as f:
    for n in notes:
        f.write(json.dumps(n) + "\n")

print(f"patients={len(patients)} encounters={len(encounters)} (dirty={len(dirty)}) notes={len(notes)}")
print(f"30-day readmission rate={encounters['readmitted_30d'].mean():.1%}")
