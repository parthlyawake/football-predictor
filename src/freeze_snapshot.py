import pandas as pd
import os
import subprocess

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_path = os.path.join(workspace_dir, "results.csv")

results = pd.read_csv(results_path)

# Set all 17 RO32 matches to NaN (pre-tournament snapshot)
results.loc[49477:49493, ['home_score', 'away_score']] = [None, None]

results.to_csv(results_path, index=False)
print("Froze results.csv at pre-tournament snapshot.")

# Re-run refresh_results.py to update Parquet files
subprocess.run(["python", "src/refresh_results.py"], check=True)
print("Re-ran refresh_results.py successfully.")
