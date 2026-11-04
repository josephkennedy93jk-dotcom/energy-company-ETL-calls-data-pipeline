import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import storage

# Paths are relative to this script, which sits in the python Files folder
ROOT = Path(__file__).resolve().parent.parent

JSON_DIR = ROOT / "JSON Raw Call Files"
BRONZE_FILE = ROOT / "calls_bronze.csv"
SILVER_FILE = ROOT / "calls_silver.csv"

PROJECT = "customer-call-data"
BUCKET = "calls_storage_energy"

UPLOAD_TIMEOUT = 60
PROGRESS_EVERY = 100
SKIP_EXISTING = {"raw"}
FORCE_RAW_UPLOAD = False

# Check everything exists first
if not JSON_DIR.is_dir():
    folders = [p.name for p in ROOT.iterdir() if p.is_dir()]
    print(f"Raw folder not found: {JSON_DIR}")
    print(f"Folders in the project folder: {folders}")
    sys.exit(1)

raw_files = sorted(JSON_DIR.glob("*.json"))
if not raw_files:
    sys.exit(f"No .json files found in {JSON_DIR}")

for csv_file in (BRONZE_FILE, SILVER_FILE):
    if not csv_file.is_file():
        sys.exit(f"File not found: {csv_file}")

bucket = storage.Client(project=PROJECT).bucket(BUCKET)

layers = {
    "raw": raw_files,
    "bronze": [BRONZE_FILE],
    "silver": [SILVER_FILE],
}

manifest = {
    "uploaded_at_utc": datetime.now(timezone.utc).isoformat(),
    "layers": {},
}

for layer, files in layers.items():
    uploaded = []
    skipped = []
    failed = []
    print(f"Uploading {layer} ({len(files)} files)...")

    existing = set()
    for b in bucket.list_blobs(prefix=f"{layer}/"):
        if not b.name.endswith("/"):
            existing.add(b.name)

    skip_layer = layer in SKIP_EXISTING
    if layer == "raw" and FORCE_RAW_UPLOAD:
        skip_layer = False

    for i, file in enumerate(files, 1):
        blob_name = f"{layer}/{file.name}"
        if skip_layer and blob_name in existing:
            skipped.append(file.name)
        else:
            try:
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file), timeout=UPLOAD_TIMEOUT)
                uploaded.append(file.name)
            except Exception as err:
                failed.append({"file": file.name, "error": str(err)})
                print(f"  FAILED {file.name}: {err}")
        if i % PROGRESS_EVERY == 0:
            print(f"  {layer}: {i}/{len(files)} processed")

    in_bucket = 0
    for b in bucket.list_blobs(prefix=f"{layer}/"):
        if not b.name.endswith("/"):
            in_bucket += 1

    manifest["layers"][layer] = {
        "local_files": len(files),
        "uploaded": len(uploaded),
        "skipped": len(skipped),
        "failed": len(failed),
        "in_bucket": in_bucket,
        "files_uploaded": uploaded,
        "failures": failed,
    }

    summary = f"{layer}: local {len(files)}, uploaded {len(uploaded)}"
    summary += f", skipped {len(skipped)}, failed {len(failed)}"
    summary += f", in bucket {in_bucket}"
    print(summary)

    if in_bucket != len(files) or failed:
        print(f"WARNING: {layer} does not match, check the manifest")

# Save the manifest at the top of the bucket
manifest_blob = bucket.blob("_manifest.json")
manifest_blob.upload_from_string(
    json.dumps(manifest, indent=2),
    content_type="application/json",
    timeout=UPLOAD_TIMEOUT,
)

# Print the file list
print("")
print("Files loaded:")
for layer, files in layers.items():
    names = [f.name for f in files]
    if len(names) <= 3:
        shown = names
    else:
        shown = [names[0], "...", names[-1]]
    print(f"  {layer}: {len(names)} files {shown}")

# Exit with an error if anything failed
total_failed = 0
for info in manifest["layers"].values():
    total_failed += info["failed"]

if total_failed > 0:
    sys.exit("Some uploads failed. Check the manifest and rerun.")