"""Ask the Pinecrest Genie space business questions via the Genie Conversation API and log
each question, the SQL Genie generated, the rows it returned and its text answer.

    python3 05_genie/ask_genie.py > evidence/05_genie_conversations.md
"""
import json
import subprocess
import time

PROFILE = "fe-east"
SPACE_ID = "01f1dc8c44ba155391aaea55a2d641cc"  # "Pinecrest Readmission Insights"
QUESTIONS = [
    "How many high-risk patients does each facility have?",
    "Which high-risk patients have no follow-up visit scheduled? Show the top 5 by risk score.",
    "Which facility had the highest overall readmission rate for COPD?",
    "What is the average predicted readmission risk by discharge disposition?",
]


def api(method: str, path: str, body: dict | None = None) -> dict:
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout if "{" in p.stdout else p.stderr
    return json.JSONDecoder().raw_decode(out[out.find("{"):])[0]


base = f"/api/2.0/genie/spaces/{SPACE_ID}"
print(f"# Genie conversations — space `{SPACE_ID}` (Pinecrest Readmission Insights)\n")
print("Asked through the Genie Conversation API. Tables: pc_gold_readmission_risk, "
      "pc_gold_discharge_features, pc_gold_facility_readmissions.\n")
for q in QUESTIONS:
    m = api("post", f"{base}/start-conversation", {"content": q})
    conv, msg = m["conversation_id"], m["message_id"]
    for _ in range(60):
        m = api("get", f"{base}/conversations/{conv}/messages/{msg}")
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)
    print(f"## Q: {q}\n\nstatus: **{m.get('status')}** · conversation `{conv}` · message `{msg}`\n")
    for att in m.get("attachments", []):
        if "query" in att:
            print(f"Generated SQL:\n```sql\n{att['query']['query']}\n```\n")
            res = api("get", f"{base}/conversations/{conv}/messages/{msg}/attachments/{att['attachment_id']}/query-result")
            sr = res.get("statement_response", {})
            cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            rows = sr.get("result", {}).get("data_array", []) or []
            if cols:
                print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
                for r in rows[:10]:
                    print("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
                print()
        if "text" in att:
            print(f"Genie answer:\n\n> " + att["text"]["content"].replace("\n", "\n> ") + "\n")
