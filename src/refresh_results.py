import pandas as pd
import os

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")
results_path = os.path.join(workspace_dir, "results.csv")

print("=== Refreshing results.csv with June 30 Completed Matches ===")
results = pd.read_csv(results_path)

# Print current rows
print("Before update:")
print(results.iloc[49481:49484].to_string())

# Update scores:
# Ivory Coast vs Norway: Norway won 2-1. Ivory Coast was home (49481). Score: 1 - 2
# results.loc[49481, 'home_score'] = 1.0
# results.loc[49481, 'away_score'] = 2.0

# France vs Sweden: France won 3-0. France was home (49482). Score: 3 - 0
# results.loc[49482, 'home_score'] = 3.0
# results.loc[49482, 'away_score'] = 0.0

# Mexico vs Ecuador: Mexico won 2-0. Mexico was home (49483). Score: 2 - 0
# results.loc[49483, 'home_score'] = 2.0
# results.loc[49483, 'away_score'] = 0.0

print("\nAfter update:")
print(results.iloc[49481:49484].to_string())

# Save results.csv back
results.to_csv(results_path, index=False)
print(f"Updated results.csv successfully.")

# Regenerate cleaned intl_team_match.parquet
former_names = pd.read_csv(os.path.join(workspace_dir, "former_names.csv"))
former_names['start_date'] = pd.to_datetime(former_names['start_date'])
former_names['end_date'] = pd.to_datetime(former_names['end_date'])

def collapse_teams(df, team_cols, date_col):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    
    num_replacements = 0
    for _, row in former_names.iterrows():
        current = row['current']
        former = row['former']
        start = row['start_date']
        end = row['end_date']
        
        for col in team_cols:
            mask = (df[col] == former) & (df[date_col] >= start) & (df[date_col] <= end)
            replaced = mask.sum()
            if replaced > 0:
                df.loc[mask, col] = current
                num_replacements += replaced
                
    print(f"  Table replacement count in {date_col}: {num_replacements}")
    return df

print("\nRegenerating intl_team_match.parquet...")
results_clean = collapse_teams(results, ['home_team', 'away_team'], 'date')
intl_match_path = os.path.join(data_dir, "intl_team_match.parquet")
results_clean.to_parquet(intl_match_path, index=False)
print(f"Saved regenerated {intl_match_path} ({len(results_clean)} rows)")
