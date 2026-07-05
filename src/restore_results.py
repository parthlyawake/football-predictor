import pandas as pd
import os
import subprocess

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_path = os.path.join(workspace_dir, "results.csv")

results = pd.read_csv(results_path)

# Restore July 1 matches to verified scores
results.loc[49484, ['home_score', 'away_score']] = [2.0, 1.0]
results.loc[49485, ['home_score', 'away_score']] = [3.0, 2.0]
results.loc[49486, ['home_score', 'away_score']] = [2.0, 0.0]

results.to_csv(results_path, index=False)
print("Restored July 1 matches to verified scores.")

# Re-run refresh_results.py to update Parquet files
subprocess.run(["python", "src/refresh_results.py"], check=True)
print("Re-ran refresh_results.py successfully.")
