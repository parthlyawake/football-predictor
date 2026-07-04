import pandas as pd
import numpy as np
import unicodedata
import re
import os

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")
os.makedirs(data_dir, exist_ok=True)

# 1. Print schemas, dtypes, row counts and validate against descriptions
files_desc = {
    "players_master.csv": ["now_cost", "selected_by_percent", "ict_index", "defensive_contribution", "corners_and_indirect_freekicks_order", "direct_freekicks_order", "penalties_order", "position", "status"],
    "player_gameweek_history.csv": ["element", "fixture", "opponent_team", "total_points", "was_home", "kickoff_time", "round", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals", "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "bps", "value", "selected"],
    "league_player_stats.csv": ["id", "player_name", "games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes", "npg", "npxG", "xGChain", "xGBuildup", "league", "league_name", "season"],
    "player_match_data.csv": ["goals", "shots", "xG", "time", "position", "h_team", "a_team", "h_goals", "a_goals", "date", "id", "season", "roster_id", "xA", "assists", "key_passes", "npg", "npxG", "xGChain", "xGBuildup", "player_id", "player_name"],
    "former_names.csv": ["current", "former", "start_date", "end_date"],
    "results.csv": ["date", "home_team", "away_team", "home_score", "away_score", "tournament", "city", "country", "neutral"],
    "goalscorers.csv": ["date", "home_team", "away_team", "team", "scorer", "minute", "own_goal", "penalty"],
    "shootouts.csv": ["date", "home_team", "away_team", "winner", "first_shooter"]
}

print("=== Phase 1: Schema Validation ===")
for filename, req_cols in files_desc.items():
    filepath = os.path.join(workspace_dir, filename)
    if not os.path.exists(filepath):
        print(f"WARNING: File {filename} not found in workspace!")
        continue
    df = pd.read_csv(filepath, nrows=5)
    row_count = sum(1 for _ in open(filepath, encoding='utf-8', errors='ignore')) - 1
    print(f"File: {filename} ({row_count} rows)")
    missing_cols = [col for col in req_cols if col not in df.columns]
    if missing_cols:
        print(f"  WARNING: Missing expected columns: {missing_cols}")
    else:
        print("  All expected columns present.")

# Load datasets
pm = pd.read_csv(os.path.join(workspace_dir, "players_master.csv"))
pgh = pd.read_csv(os.path.join(workspace_dir, "player_gameweek_history.csv"))
us_stats = pd.read_csv(os.path.join(workspace_dir, "league_player_stats.csv"))
former_names = pd.read_csv(os.path.join(workspace_dir, "former_names.csv"))
results = pd.read_csv(os.path.join(workspace_dir, "results.csv"))
goalscorers = pd.read_csv(os.path.join(workspace_dir, "goalscorers.csv"))
shootouts = pd.read_csv(os.path.join(workspace_dir, "shootouts.csv"))

# 2. Name Normalization
def normalize_name(name):
    if not isinstance(name, str):
        return ""
    # Map special characters that NFKD drops or doesn't map to plain ASCII
    replacements = {
        'ı': 'i', 'İ': 'I',
        'ğ': 'g', 'Ğ': 'G',
        'ş': 's', 'Ş': 'S',
        'ç': 'c', 'Ç': 'C',
        'ö': 'o', 'Ö': 'O',
        'ü': 'u', 'Ü': 'U',
        'Ø': 'O', 'ø': 'o',
        'Æ': 'Ae', 'æ': 'ae',
        'ß': 'ss',
        'Đ': 'D', 'đ': 'd',
        'Ł': 'L', 'ł': 'l',
        'œ': 'oe', 'Œ': 'OE'
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('utf-8')
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Team mapping between FPL and Understat
team_mapping = {
    'Man City': 'Manchester City',
    'Man Utd': 'Manchester United',
    'Newcastle': 'Newcastle United',
    "Nott'm Forest": 'Nottingham Forest',
    'Spurs': 'Tottenham',
    'Wolves': 'Wolverhampton Wanderers'
}

def clean_team_name(t):
    return team_mapping.get(t, t)

# Prepare name fields
pm['clean_team'] = pm['team_name'].apply(clean_team_name)
pm['norm_full'] = (pm['first_name'] + " " + pm['second_name']).apply(normalize_name)
pm['norm_web'] = pm['web_name'].apply(normalize_name)
pm['norm_known'] = pm['known_name'].apply(normalize_name)

us_players = us_stats[['id', 'player_name', 'team_title', 'league']].drop_duplicates().copy()
us_players['norm_name'] = us_players['player_name'].apply(normalize_name)
us_players['teams'] = us_players['team_title'].apply(lambda x: [t.strip() for t in x.split(',')] if isinstance(x, str) else [])

# Manual mappings for the 7 active unmatched players
manual_mapping = {
    148: 13066, # Ferdi Kadıoğlu -> Ferdi Kadioglu
    129: 11772, # Yehor Yarmoliuk -> Yehor Yarmolyuk
    713: 12168, # Álex Jiménez Sánchez -> Alejandro Jiménez
    712: 9024,  # Yéremy Pino Santos -> Yeremi Pino
    612: 7365,  # Lucas Tolentino Coelho de Lima -> Lucas Paquetá
    645: 13200, # Fer López González -> Fernando López
    607: 6935,  # Nayef Aguerd -> Naif Aguerd
}

# 3. Identity Matching
fpl_to_understat = {}
match_reasons = {}

for idx, fpl_row in pm.iterrows():
    fpl_id = fpl_row['id']
    
    # Check manual mapping first
    if fpl_id in manual_mapping:
        fpl_to_understat[fpl_id] = manual_mapping[fpl_id]
        match_reasons[fpl_id] = "manual_mapping"
        continue
        
    fpl_team = fpl_row['clean_team']
    fpl_full = fpl_row['norm_full']
    fpl_web = fpl_row['norm_web']
    fpl_known = fpl_row['norm_known']
    
    # Filter candidates by team (if team in Understat)
    candidates = us_players[us_players['teams'].apply(lambda ts: fpl_team in ts)]
    if len(candidates) == 0:
        candidates = us_players[us_players['league'] == 'EPL']
    if len(candidates) == 0:
        candidates = us_players
        
    found_id = None
    
    # Try strategies in order
    # A. Exact full name
    match1 = candidates[candidates['norm_name'] == fpl_full]
    if len(match1) == 1:
        found_id = match1.iloc[0]['id']
        reason = "exact_full"
        
    # B. Exact known name
    if found_id is None and fpl_known:
        match2 = candidates[candidates['norm_name'] == fpl_known]
        if len(match2) == 1:
            found_id = match2.iloc[0]['id']
            reason = "exact_known"
            
    # C. Exact web name
    if found_id is None and fpl_web:
        match3 = candidates[candidates['norm_name'] == fpl_web]
        if len(match3) == 1:
            found_id = match3.iloc[0]['id']
            reason = "exact_web"
            
    # D. Token overlap matching within team
    if found_id is None:
        fpl_tokens = set(fpl_full.split())
        fpl_web_tokens = set(fpl_web.split())
        best_cand = None
        best_overlap = 0
        for c_idx, c_row in candidates.iterrows():
            c_tokens = set(c_row['norm_name'].split())
            is_subset = c_tokens.issubset(fpl_tokens) or fpl_tokens.issubset(c_tokens) or fpl_web_tokens.issubset(c_tokens)
            if is_subset:
                overlap = len(c_tokens.intersection(fpl_tokens))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_cand = c_row['id']
        if best_overlap >= 1:
            found_id = best_cand
            reason = "token_overlap"
            
    if found_id is not None:
        fpl_to_understat[fpl_id] = found_id
        match_reasons[fpl_id] = reason

# Map understat player id back to players_master
pm['understat_id'] = pm['id'].map(fpl_to_understat)

# Compute match rates and write unmatched report
unmatched_pm = pm[pm['understat_id'].isna()]
match_rate = len(fpl_to_understat) / len(pm)
print(f"\nIdentity Matching Results:")
print(f"  Total FPL Players: {len(pm)}")
print(f"  Successfully Matched: {len(fpl_to_understat)}")
print(f"  Unmatched: {len(unmatched_pm)}")
print(f"  Match Rate: {match_rate:.2%}")

# Enrich unmatched players with their minutes and points in history to verify impact
unmatched_stats = pgh[pgh['element'].isin(unmatched_pm['id'])].groupby('element').agg({
    'minutes': 'sum',
    'total_points': 'sum'
}).reset_index()

unmatched_report = pd.merge(
    unmatched_pm[['id', 'first_name', 'second_name', 'web_name', 'team_name']],
    unmatched_stats,
    left_on='id',
    right_on='element',
    how='left'
).fillna(0)

unmatched_report['minutes'] = unmatched_report['minutes'].astype(int)
unmatched_report['total_points'] = unmatched_report['total_points'].astype(int)

unmatched_filepath = os.path.join(data_dir, "unmatched_players.csv")
unmatched_report.to_csv(unmatched_filepath, index=False, encoding='utf-8')
print(f"Unmatched report written to {unmatched_filepath}")

active_unmatched_count = len(unmatched_report[unmatched_report['minutes'] > 0])
print(f"  Active Unmatched Players (minutes > 0): {active_unmatched_count}")

# 4. Track B: Team name collapsing
print("\n=== Phase 1: Team Name Collapsing ===")
former_names['start_date'] = pd.to_datetime(former_names['start_date'])
former_names['end_date'] = pd.to_datetime(former_names['end_date'])

def collapse_teams(df, team_cols, date_col):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Track changed counts
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

results_clean = collapse_teams(results, ['home_team', 'away_team'], 'date')
goalscorers_clean = collapse_teams(goalscorers, ['home_team', 'away_team', 'team'], 'date')
shootouts_clean = collapse_teams(shootouts, ['home_team', 'away_team', 'winner'], 'date')

# 5. Output Parquet Files
print("\n=== Phase 1: Saving Parquet Tables ===")

# Track A: player gameweek table enriched with understat_id and player master info
# Merge elements info first
pgh_clean = pd.merge(
    pgh,
    pm[['id', 'first_name', 'second_name', 'web_name', 'team_name', 'position', 'status', 'chance_of_playing_next_round', 
        'corners_and_indirect_freekicks_order', 'direct_freekicks_order', 'penalties_order', 'understat_id']],
    left_on='element',
    right_on='id',
    how='left'
)
# Drop extra column 'id' from pm merge
pgh_clean = pgh_clean.drop(columns=['id'])

# Save to parquet
club_parquet_path = os.path.join(data_dir, "club_player_gameweek.parquet")
pgh_clean.to_parquet(club_parquet_path, index=False)
print(f"Saved {club_parquet_path} ({len(pgh_clean)} rows)")

# Track B: Save clean international tables
intl_match_path = os.path.join(data_dir, "intl_team_match.parquet")
results_clean.to_parquet(intl_match_path, index=False)
print(f"Saved {intl_match_path} ({len(results_clean)} rows)")

intl_goals_path = os.path.join(data_dir, "intl_goalscorers.parquet")
goalscorers_clean.to_parquet(intl_goals_path, index=False)
print(f"Saved {intl_goals_path} ({len(goalscorers_clean)} rows)")

intl_shootouts_path = os.path.join(data_dir, "intl_shootouts.parquet")
shootouts_clean.to_parquet(intl_shootouts_path, index=False)
print(f"Saved {intl_shootouts_path} ({len(shootouts_clean)} rows)")

print("\nPhase 1 Completed Successfully!")
