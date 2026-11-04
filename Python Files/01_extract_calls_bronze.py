import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "JSON Raw Call Files"
OUT = ROOT / "calls_bronze.csv"

rows = []
for f in sorted(JSON_DIR.glob("*.json")):
    d = json.loads(f.read_text())
    t = d["transcription"]
    a = d["ccai_analysis"]
    c = a["compliance_checks"]
    rows.append({
        "source_file": f.name,
        "call_id": d["call_id"],
        "agent_id": d.get("agent_id"),
        "campaign": d["campaign"],
        "direction": d["direction"],
        "start_time": d["start_time"],
        "end_time": d["end_time"],
        "duration_seconds": d["duration_seconds"],
        "queue_wait_seconds": d["queue_wait_seconds"],
        "engine_confidence": t["engine_confidence"],
        "language": t["language"],
        "n_turns": len(t["turns"]),
        "overall_sentiment": a["overall_sentiment"],
        "sentiment_score": a["sentiment_score"],
        "customer_intent": a["customer_intent"],
        "topics": "|".join(a["topics"]),
        "cancellation_rights_read": c["cancellation_rights_read"],
        "exit_fee_disclosed": c["exit_fee_disclosed"],
        "call_recording_notice_given": c["call_recording_notice_given"],
        "talk_ratio_agent": a["talk_ratio_agent"],
        "silence_seconds": a["silence_seconds"],
        "agent_assist_prompts_shown": a["agent_assist_prompts_shown"],
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print("rows:", len(df), "| unique call_ids:", df.call_id.nunique())
print("missing agent_id:", df.agent_id.isna().sum())
print("duplicate call_ids:", df[df.call_id.duplicated(keep=False)][["source_file", "call_id"]].to_string(index=False))
