"""Pinecrest Care Coordinator — Databricks App (Streamlit).

Reads the ML risk worklist + care notes from Lakebase (synced from Unity Catalog), explains a
patient's risk with an LLM, and writes the coordinator's approved action back to a writable
Lakebase table (pinecrest.care_actions).
"""
import streamlit as st

import backend as be

st.set_page_config(page_title="Pinecrest Care Coordinator", layout="wide")
st.title("Pinecrest Health · 30-day Readmission Worklist")
st.caption("Risk scores from the pc_readmission_risk_model, served from Lakebase. All data is synthetic.")

facilities = ["All"] + be.facilities()
c1, c2 = st.columns([1, 1])
facility = c1.selectbox("Facility", facilities)
tier = c2.selectbox("Risk tier", ["High", "Medium", "Low", "All"])

work = be.worklist(None if facility == "All" else facility, None if tier == "All" else tier)
k1, k2, k3 = st.columns(3)
k1.metric("Patients on worklist", len(work))
k2.metric("Avg risk", f"{work['risk_score'].mean():.0%}" if len(work) else "–")
k3.metric("Actions approved today", be.actions_today())
st.dataframe(work, hide_index=True, use_container_width=True)

if len(work):
    st.subheader("Review a patient")
    pid = st.selectbox("Patient", work["patient_id"].tolist())
    row = work[work["patient_id"] == pid].iloc[0]
    notes = be.notes(pid)
    left, right = st.columns([1, 1])
    with left:
        st.write(f"**Risk:** {row.risk_score:.0%} ({row.risk_tier}) · **Condition:** {row.primary_condition} · "
                 f"**Disposition:** {row.discharge_disposition} · **Follow-up booked:** {row.followup_scheduled}")
        st.write("**Coordinator notes**")
        for n in notes:
            st.write(f"- {n['note_date']}: {n['note_text']}")
        if st.button("Explain risk with AI"):
            with st.spinner("Asking the model..."):
                st.session_state[f"explain_{pid}"] = be.explain(row.to_dict(), notes)
        if f"explain_{pid}" in st.session_state:
            st.info(st.session_state[f"explain_{pid}"])
    with right:
        action = st.text_input("Action", row.recommended_action)
        coordinator_note = st.text_area("Note", "")
        if st.button("Approve action", type="primary"):
            action_id = be.approve(pid, row.encounter_id, action, coordinator_note, be.current_user())
            st.success(f"Saved action {action_id} to Lakebase")

st.subheader("Recent approved actions")
st.dataframe(be.recent_actions(), hide_index=True, use_container_width=True)
