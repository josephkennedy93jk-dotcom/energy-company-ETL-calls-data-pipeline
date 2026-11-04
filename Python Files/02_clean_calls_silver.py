from pathlib import Path
import pandas as pd

# Paths are relative to this script so it runs the same on any machine
ROOT = Path(__file__).resolve().parent.parent
BRONZE_FILE = ROOT / "calls_bronze.csv"
CRM_FILE = ROOT / "crm_export.csv"
SILVER_FILE = ROOT / "calls_silver.csv"
QUARANTINE_FILE = ROOT / "calls_quarantine.csv"
LOG_FILE = ROOT / "calls_cleaning_log.csv"

# Only these three campaigns are real, anything else gets flagged
VALID_CAMPAIGNS = {"fixed_tariff_renewal", "new_customer_switch", "winback"}

# Every change we make gets added here so nothing happens silently
log = []


def note(call_id, issue, action):
    # Adds one line to the log: which call, what was wrong, what we did
    log.append({"call_id": call_id, "issue": issue, "action": action})


def fix_types(df):
    # Tidy the column names, then turn the time columns into real dates
    # and the compliance flags into true/false. Dates that can't be read become empty
    df.columns = [c.strip().lower() for c in df.columns]
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True, errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], utc=True, errors="coerce")
    for col in ["cancellation_rights_read", "exit_fee_disclosed", "call_recording_notice_given"]:
        df[col] = df[col].astype(bool)
    return df


def fix_call_ids(df):
    # The number at the end of the file name is the call's true position,
    # so if the call_id inside the file disagrees, trust the file name.
    # This is what catches C0199 appearing twice
    file_num = df["source_file"].str.extract(r"_(\d+)\.json")[0].astype(int)
    expected = "C" + file_num.astype(str).str.zfill(4)
    wrong = df["call_id"] != expected
    for _, row in df[wrong].iterrows():
        note(row["call_id"], "call_id does not match filename " + row["source_file"], "replaced from filename")
    df.loc[wrong, "call_id"] = expected[wrong]
    return df


def fix_missing_agents(df):
    # Don't guess who the agent was. Mark it unknown and log it
    missing = df["agent_id"].isna()
    for cid in df.loc[missing, "call_id"]:
        note(cid, "agent_id missing", "set to unknown")
    df["agent_id"] = df["agent_id"].fillna("unknown")
    return df


def standardise_text(df):
    # Strip stray spaces and force lower case so the same value is never spelled two ways.
    # Agent IDs keep their case because A11 is a name, not a word
    for col in ["campaign", "direction", "agent_id", "overall_sentiment", "customer_intent"]:
        df[col] = df[col].astype(str).str.strip().str.lower() if col != "agent_id" else df[col].astype(str).str.strip()
    return df


def validate(df):
    # Each check below finds rows that don't make sense.
    # Bad rows are logged and moved to quarantine, not deleted
    bad = pd.Series(False, index=df.index)
    checks = {
        "sentiment_score outside -1 to 1": ~df["sentiment_score"].between(-1, 1),
        "duration not above zero": ~(df["duration_seconds"] > 0),
        "end_time not after start_time": ~(df["end_time"] > df["start_time"]),
        "unknown campaign": ~df["campaign"].isin(VALID_CAMPAIGNS),
        "unparseable timestamp": df["start_time"].isna() | df["end_time"].isna(),
    }
    for issue, mask in checks.items():
        for cid in df.loc[mask, "call_id"]:
            note(cid, issue, "quarantined")
        bad |= mask
    # Last check: after the ID fix, no call_id should appear twice
    dupes = df["call_id"].duplicated(keep=False)
    for cid in df.loc[dupes, "call_id"]:
        note(cid, "duplicate call_id after fixes", "quarantined")
    bad |= dupes
    return df[~bad].copy(), df[bad].copy()


def join_crm(df):
    # Attach the sale outcome from the CRM file using call_id.
    # A left join keeps every call even if the CRM has nothing on it
    crm = pd.read_csv(CRM_FILE)
    merged = df.merge(crm, on="call_id", how="left", indicator=True)
    # Calls with no CRM row get logged but stay in the table
    for cid in merged.loc[merged["_merge"] == "left_only", "call_id"]:
        note(cid, "no CRM record", "kept, outcome empty")
    # The other direction: CRM rows with no matching call are only reported
    for cid in set(crm["call_id"]) - set(df["call_id"]):
        note(cid, "CRM record with no call", "reported only")
    return merged.drop(columns="_merge")


if __name__ == "__main__":
    # Run the steps in order: bronze in, silver and quarantine and log out
    bronze = pd.read_csv(BRONZE_FILE)
    df = fix_types(bronze)
    df = fix_call_ids(df)
    df = fix_missing_agents(df)
    df = standardise_text(df)
    silver, quarantine = validate(df)
    silver = join_crm(silver)

    silver.to_csv(SILVER_FILE, index=False)
    quarantine.to_csv(QUARANTINE_FILE, index=False)
    pd.DataFrame(log).to_csv(LOG_FILE, index=False)

    # Quick summary so you can see the counts add up
    print("bronze rows:", len(bronze))
    print("silver rows:", len(silver))
    print("quarantined:", len(quarantine))
    print("log entries:", len(log))