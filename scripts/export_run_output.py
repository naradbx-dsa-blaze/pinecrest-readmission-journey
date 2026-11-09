"""Export a Databricks notebook job run as readable text: every cell's code and its output.

    python3 scripts/export_run_output.py <job_run_id> evidence/03_ml_training_run_output.md "ML training run"
"""
import base64
import html
import json
import re
import subprocess
import sys
import urllib.parse

PROFILE = "fe-east"


def cli(*args) -> dict:
    p = subprocess.run(["databricks", *args, "--profile", PROFILE, "-o", "json"], capture_output=True, text=True)
    out = p.stdout if "{" in p.stdout else p.stderr
    return json.JSONDecoder().raw_decode(out[out.find("{"):])[0]


run_id, out_path, title = sys.argv[1], sys.argv[2], sys.argv[3]
run = cli("jobs", "get-run", run_id)
task = run["tasks"][0]
state = task.get("state", {}).get("result_state") or run.get("state", {}).get("result_state")
content = cli("jobs", "export-run", str(task["run_id"]), "--views-to-export", "CODE")["views"][0]["content"]
model = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", content).group(1)
nb = json.loads(urllib.parse.unquote(base64.b64decode(model).decode()))

doc = [f"# {title}\n",
       f"Job run `{run_id}` (task run `{task['run_id']}`) · result **{state}** · "
       f"notebook `{task.get('notebook_task', {}).get('notebook_path', '')}`\n"]
for cmd in nb["commands"]:
    data = (cmd.get("results") or {}).get("data")
    text = data if isinstance(data, str) else "\n".join(
        x.get("data", "") if isinstance(x, dict) else str(x) for x in (data or []))
    text = re.sub(r"\x1b\[[0-9;]*m", "", re.sub(r"<[^>]+>", "", html.unescape(str(text)))).strip()
    doc.append(f"### cell\n```python\n{cmd['command'].strip()}\n```\n**output:**\n```\n{text[:30000]}\n```\n")
open(out_path, "w").write("\n".join(doc))
print(f"wrote {out_path}: {len(nb['commands'])} cells, result {state}")
