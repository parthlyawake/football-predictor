import pandas as pd
import os
import subprocess

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")
results_path = os.path.join(workspace_dir, "results.csv")
goalscorers_path = os.path.join(workspace_dir, "goalscorers.csv")

print("=== Updating results.csv ===")
results = pd.read_csv(results_path)

# Print July 1 rows before update
print("Before update:")
print(results.iloc[49484:49487].to_string())

# Row 49484: England vs DR Congo (July 1) -> Score: 2 - 1
results.loc[49484, 'home_score'] = 2.0
results.loc[49484, 'away_score'] = 1.0

# Row 49485: Belgium vs Senegal (July 1) -> Score: 3 - 2
results.loc[49485, 'home_score'] = 3.0
results.loc[49485, 'away_score'] = 2.0

# Row 49486: United States vs Bosnia and Herzegovina (July 1) -> Score: 2 - 0
results.loc[49486, 'home_score'] = 2.0
results.loc[49486, 'away_score'] = 0.0

print("\nAfter update:")
print(results.iloc[49484:49487].to_string())
results.to_csv(results_path, index=False)
print("Saved results.csv successfully.")

print("\n=== Updating goalscorers.csv ===")
goalscorers = pd.read_csv(goalscorers_path)

# New goals to append
new_goals = [
    # England vs DR Congo
    {"date": "2026-07-01", "home_team": "England", "away_team": "DR Congo", "team": "DR Congo", "scorer": "Brian Cipenga", "minute": 7.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "England", "away_team": "DR Congo", "team": "England", "scorer": "Harry Kane", "minute": 75.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "England", "away_team": "DR Congo", "team": "England", "scorer": "Harry Kane", "minute": 86.0, "own_goal": False, "penalty": False},
    # Belgium vs Senegal
    {"date": "2026-07-01", "home_team": "Belgium", "away_team": "Senegal", "team": "Senegal", "scorer": "Habib Diarra", "minute": 25.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "Belgium", "away_team": "Senegal", "team": "Senegal", "scorer": "Ismaila Sarr", "minute": 51.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "Belgium", "away_team": "Senegal", "team": "Belgium", "scorer": "Romelu Lukaku", "minute": 86.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "Belgium", "away_team": "Senegal", "team": "Belgium", "scorer": "Youri Tielemans", "minute": 89.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "Belgium", "away_team": "Senegal", "team": "Belgium", "scorer": "Youri Tielemans", "minute": 120.0, "own_goal": False, "penalty": True},
    # United States vs Bosnia and Herzegovina
    {"date": "2026-07-01", "home_team": "United States", "away_team": "Bosnia and Herzegovina", "team": "United States", "scorer": "Folarin Balogun", "minute": 45.0, "own_goal": False, "penalty": False},
    {"date": "2026-07-01", "home_team": "United States", "away_team": "Bosnia and Herzegovina", "team": "United States", "scorer": "Malik Tillman", "minute": 82.0, "own_goal": False, "penalty": False}
]

df_new_goals = pd.DataFrame(new_goals)
goalscorers = pd.concat([goalscorers, df_new_goals], ignore_index=True)
goalscorers.to_csv(goalscorers_path, index=False)
print("Saved goalscorers.csv successfully.")

print("\n=== Running refresh_results.py ===")
subprocess.run(["python", "src/refresh_results.py"], check=True)

print("\n=== Running clean_data.py ===")
subprocess.run(["python", "src/clean_data.py"], check=True)

print("\nKnockout matches update completed successfully!")
