import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
N_CALLS = 1000
N_BAD = 47
OUT_DIR = Path(r"C:\Users\guest1\OneDrive\Desktop\data analytics portfolio projects\AI Call center data pipeline\JSON Raw Call Files")
CRM_FILE = OUT_DIR.parent / "crm_export.csv"
TRUTH_FILE = OUT_DIR.parent / "bad_behaviour_truth.csv"

random.seed(SEED)
OUT_DIR.mkdir(parents=True, exist_ok=True)

AGENTS = {f"A{i:02d}": random.uniform(-0.08, 0.10) for i in range(1, 13)}
CAMPAIGNS = ["fixed_tariff_renewal", "new_customer_switch", "winback"]
OBJECTIONS = {
    "price": ("How much is this going to cost me?", -0.15),
    "contract_length": ("Two years is a long time though.", -0.10),
    "exit_fees": ("What if I want to leave early?", -0.08),
    "need_to_think": ("I need to think about it.", -0.20),
}
AGENT_LINES = [
    "Hello, this is {name} calling about your energy plan. Is now a good time?",
    "Your current rate ends soon and I can offer a new fixed deal today.",
    "On your usage, this would keep your unit rate close to what you pay now.",
    "Before we go on, I need to read some important information.",
]
RUDE_LINES = [
    "Look, I haven't got all day, so listen carefully.",
    "You'd be mad not to take this, everyone else does.",
    "I've already explained that. Were you not paying attention?",
    "If you don't decide now, the price goes up and that's your problem.",
]
PRODUCTS = {"fixed_tariff_24m": (24, 1180.0), "fixed_tariff_12m": (12, 640.0)}

PLANTED = {50, 120, 200}
BAD_CALLS = set(random.sample([i for i in range(1, N_CALLS + 1) if i not in PLANTED], N_BAD))


def make_call(i, bad):
    call_id = f"C{i:04d}"
    agent_id = random.choice(list(AGENTS))
    campaign = random.choice(CAMPAIGNS)
    start = datetime(2026, 10, 1) + timedelta(
        days=random.randint(0, 27),
        hours=random.randint(8, 19),
        minutes=random.randint(0, 59),
    )
    objections = random.sample(list(OBJECTIONS), k=random.choice([0, 1, 1, 2, 3]))

    turns, t, n = [], 0.0, 1

    def add(speaker, text):
        nonlocal t, n
        length = round(max(2.0, len(text) / 14 + random.uniform(-1, 2)), 1)
        turns.append({"turn_no": n, "speaker": speaker, "start_sec": round(t, 1),
                      "end_sec": round(t + length, 1), "text": text})
        t += length + random.uniform(0.3, 1.2)
        n += 1

    add("agent", AGENT_LINES[0].format(name=agent_id))
    add("customer", "Yeah, go on.")
    add("agent", RUDE_LINES[0] if bad else AGENT_LINES[1])
    for obj in objections:
        add("customer", OBJECTIONS[obj][0])
        add("agent", random.choice(RUDE_LINES[1:3]) if bad else AGENT_LINES[2])
    if bad:
        add("agent", RUDE_LINES[3])
    rights_read = random.random() > (0.40 if bad else 0.08)
    if rights_read:
        add("agent", AGENT_LINES[3])

    p_sale = 0.45 + AGENTS[agent_id] + sum(OBJECTIONS[o][1] for o in objections)
    if not rights_read:
        p_sale -= 0.05
    if bad:
        p_sale -= 0.15
    roll = random.random()
    outcome = "sale" if roll < p_sale else random.choice(["callback", "no_sale", "no_sale"])
    add("customer", "Okay, let's do it." if outcome == "sale" else "I'll leave it for now.")

    sentiment_score = round(max(-1, min(1, 0.3 + (0.3 if outcome == "sale" else -0.2)
                            + sum(OBJECTIONS[o][1] for o in objections)
                            + (-0.4 if bad else 0) + random.uniform(-0.2, 0.2))), 2)
    duration = int(t)
    end = start + timedelta(seconds=duration)

    call = {
        "call_id": call_id,
        "agent_id": agent_id,
        "campaign": campaign,
        "direction": "outbound",
        "start_time": start.isoformat() + "Z",
        "end_time": end.isoformat() + "Z",
        "duration_seconds": duration,
        "queue_wait_seconds": 0,
        "transcription": {
            "engine_confidence": round(random.uniform(0.78, 0.98), 2),
            "language": "en-GB",
            "turns": turns,
        },
        "ccai_analysis": {
            "overall_sentiment": "positive" if sentiment_score > 0.2 else "neutral" if sentiment_score > -0.2 else "negative",
            "sentiment_score": sentiment_score,
            "topics": objections or ["general_enquiry"],
            "customer_intent": "likely_to_switch" if outcome == "sale" else "unlikely_to_switch",
            "compliance_checks": {
                "cancellation_rights_read": rights_read,
                "exit_fee_disclosed": "exit_fees" in objections or random.random() > 0.3,
                "call_recording_notice_given": random.random() > 0.1,
            },
            "talk_ratio_agent": round(random.uniform(0.5, 0.8), 2),
            "silence_seconds": round(random.uniform(0, 12), 1),
            "agent_assist_prompts_shown": random.randint(0, 5),
        },
    }

    product = random.choice(list(PRODUCTS)) if outcome == "sale" else ""
    crm = {
        "call_id": call_id,
        "disposition": outcome,
        "product_sold": product,
        "contract_months": PRODUCTS[product][0] if product else "",
        "order_value_gbp": PRODUCTS[product][1] if product else "",
    }
    return call, crm


def main():
    crm_rows, truth_rows = [], []
    for i in range(1, N_CALLS + 1):
        bad = i in BAD_CALLS
        call, crm = make_call(i, bad)
        truth_id = call["call_id"]
        if i in (50, 120):
            del call["agent_id"]
        if i == 200:
            call["call_id"] = "C0199"
        (OUT_DIR / f"{call['call_id']}_{i}.json").write_text(json.dumps(call, indent=2))
        crm_rows.append(crm)
        if bad:
            truth_rows.append(truth_id)

    header = "call_id,disposition,product_sold,contract_months,order_value_gbp"
    lines = [header] + [",".join(str(r[k]) for k in header.split(",")) for r in crm_rows]
    CRM_FILE.write_text("\n".join(lines))
    TRUTH_FILE.write_text("call_id,bad_behaviour\n" + "\n".join(f"{c},yes" for c in truth_rows))
    print(f"Wrote {N_CALLS} call files to {OUT_DIR}")
    print(f"CRM file: {CRM_FILE}")
    print(f"Answer key ({len(truth_rows)} bad calls): {TRUTH_FILE}")


if __name__ == "__main__":
    main()