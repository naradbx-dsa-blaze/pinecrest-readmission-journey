"""Data + AI access for the Pinecrest Care Coordinator app.

Lakebase (Postgres) holds two kinds of tables:
  * read-only synced tables from Unity Catalog: public.pc_risk_worklist, public.pc_care_notes
  * a writable operational table owned by the app:   pinecrest.care_actions

The app authenticates to Lakebase with its service principal's OAuth token (env vars PGHOST,
PGDATABASE, PGUSER, PGPORT, PGSSLMODE are injected by the app's database resource).
"""
import os
import uuid

import pandas as pd
import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "databricks-claude-sonnet-5-5")
_w = WorkspaceClient()


def _conn():
    return psycopg.connect(host=os.environ["PGHOST"], dbname=os.getenv("PGDATABASE", "databricks_postgres"),
                           user=os.getenv("PGUSER") or _w.current_user.me().user_name,
                           password=_w.config.oauth_token().access_token,
                           port=int(os.getenv("PGPORT", "5432")), sslmode=os.getenv("PGSSLMODE", "require"),
                           autocommit=True)


def _df(sql: str, params=()) -> pd.DataFrame:
    with _conn() as c, c.cursor() as cur:
        cur.execute(sql, params)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def ensure_schema():
    with _conn() as c:
        c.execute("""CREATE SCHEMA IF NOT EXISTS pinecrest;
            CREATE TABLE IF NOT EXISTS pinecrest.care_actions (
                action_id     UUID PRIMARY KEY,
                patient_id    TEXT NOT NULL,
                encounter_id  TEXT NOT NULL,
                action        TEXT NOT NULL,
                note          TEXT,
                status        TEXT NOT NULL DEFAULT 'approved',
                approved_by   TEXT NOT NULL,
                approved_at   TIMESTAMPTZ NOT NULL DEFAULT now())""")


def facilities() -> list[str]:
    return _df("SELECT DISTINCT facility FROM public.pc_risk_worklist ORDER BY 1")["facility"].tolist()


def worklist(facility=None, tier=None) -> pd.DataFrame:
    sql = """SELECT w.patient_id, w.facility, w.primary_condition, w.discharge_date, w.discharge_disposition,
                    w.followup_scheduled, w.risk_score, w.risk_tier, w.recommended_action, w.encounter_id,
                    a.status AS action_status
             FROM public.pc_risk_worklist w
             LEFT JOIN (SELECT DISTINCT ON (patient_id) patient_id, status FROM pinecrest.care_actions
                        ORDER BY patient_id, approved_at DESC) a USING (patient_id)
             WHERE (%s::text IS NULL OR w.facility = %s) AND (%s::text IS NULL OR w.risk_tier = %s)
             ORDER BY w.risk_score DESC LIMIT 200"""
    df = _df(sql, (facility, facility, tier, tier))
    print(f"[worklist] facility={facility} tier={tier} rows={len(df)} source=lakebase:public.pc_risk_worklist", flush=True)
    return df


def notes(patient_id: str) -> list[dict]:
    return _df("SELECT note_date, note_text FROM public.pc_care_notes WHERE patient_id = %s ORDER BY note_date DESC",
               (patient_id,)).to_dict("records")


def explain(patient: dict, patient_notes: list[dict]) -> str:
    facts = {k: str(v) for k, v in patient.items() if k not in ("action_status",)}
    prompt = ("You are a hospital care-coordination assistant. In 3 short bullet points, explain why this "
              "patient is at risk of 30-day readmission and what the coordinator should do first. "
              f"Use only these facts.\nPatient: {facts}\nNotes: {[n['note_text'] for n in patient_notes]}")
    r = _w.serving_endpoints.query(name=LLM_ENDPOINT, messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)], max_tokens=300)
    text = r.choices[0].message.content
    print(f"[explain] patient={patient.get('patient_id')} endpoint={LLM_ENDPOINT} notes={len(patient_notes)} "
          f"response={text!r}", flush=True)
    return text


def approve(patient_id, encounter_id, action, note, user) -> str:
    action_id = str(uuid.uuid4())
    with _conn() as c:
        c.execute("""INSERT INTO pinecrest.care_actions (action_id, patient_id, encounter_id, action, note, approved_by)
                     VALUES (%s, %s, %s, %s, %s, %s)""", (action_id, patient_id, encounter_id, action, note, user))
    print(f"[approve] action_id={action_id} patient={patient_id} action={action!r} by={user} -> lakebase:pinecrest.care_actions",
          flush=True)
    return action_id


def recent_actions() -> pd.DataFrame:
    return _df("SELECT action_id, patient_id, action, status, approved_by, approved_at "
               "FROM pinecrest.care_actions ORDER BY approved_at DESC LIMIT 20")


def actions_today() -> int:
    return int(_df("SELECT count(*) AS n FROM pinecrest.care_actions WHERE approved_at::date = now()::date")["n"][0])


def current_user() -> str:
    try:
        import streamlit as st
        return st.context.headers.get("X-Forwarded-Email") or "coordinator"
    except Exception:
        return "coordinator"
