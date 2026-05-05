import subprocess
import sys
import os
import time

# All pipeline steps in the order they must run.
# Each entry is (script_path, description)
STEPS = [
    ("scripts/clean.py",    "Step 1 — Clean raw data"),
    ("scripts/load_db.py",  "Step 2 — Load database"),
    ("scripts/queries.py",  "Step 3 — Run SQL queries"),
    ("scripts/reports.py",  "Step 4 — Generate reports"),
]


def run_step(script, description):
    """
    Runs a single pipeline step as a subprocess using the same Python
    interpreter that's running this script — important so the venv
    packages are used rather than the system Python.
    """
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"  Running: {script}")
    print(f"{'=' * 60}")

    start = time.time()

    result = subprocess.run(
        [sys.executable, script],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    elapsed = time.time() - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    if result.returncode != 0:
        print(f"\n  ERROR: {script} failed with exit code {result.returncode}")
        print("  Pipeline stopped. Fix the error above and re-run main.py.")
        sys.exit(result.returncode)

    print(f"\n  Completed in {minutes}m {seconds}s")


def main():
    print("=" * 60)
    print("  Global Patent Intelligence — Full Pipeline")
    print("  Run this script to reproduce all results from scratch.")
    print("=" * 60)

    pipeline_start = time.time()

    for script, description in STEPS:
        run_step(script, description)

    total = time.time() - pipeline_start
    minutes = int(total // 60)
    seconds = int(total % 60)

    print(f"\n{'=' * 60}")
    print(f"  Pipeline complete in {minutes}m {seconds}s")
    print(f"  Database : database/patents.db")
    print(f"  Reports  : output/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
