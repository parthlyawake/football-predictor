import pandas as pd
import os
import subprocess

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
results_path = os.path.join(workspace_dir, "results.csv")

results = pd.read_csv(results_path)

# Set July 1 matches back to NaN
results.loc[49484, ['home_score', 'away_score']] = [None, None]
results.loc[49485, ['home_score', 'away_score']] = [None, None]
results.loc[49486, ['home_score', 'away_score']] = [None, None]

results.to_csv(results_path, index=False)
print("Reverted July 1 matches in results.csv to NaN.")

# Re-run refresh_results.py
subprocess.run(["python", "src/refresh_results.py"], check=True)
print("Re-ran refresh_results.py successfully.")
