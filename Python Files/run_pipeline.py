import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

STEPS = [
    "01_extract_calls_bronze.py",
    "02_clean_calls_silver.py",
    "03_load_callsdata_cloud.py",
]


def run_step(script):
    print(f"\n=== Running {script} ===")
    start = time.time()
    result = subprocess.run([sys.executable, str(HERE / script)], cwd=HERE)
    seconds = round(time.time() - start, 1)
    if result.returncode != 0:
        print(f"FAILED: {script} (exit code {result.returncode}) after {seconds}s")
        sys.exit(result.returncode)
    print(f"Done: {script} in {seconds}s")


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    total_start = time.time()
    for script in STEPS[first - 1:]:
        run_step(script)
    print(f"\nPipeline finished in {round(time.time() - total_start, 1)}s")


if __name__ == "__main__":
    main()