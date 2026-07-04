import pandas as pd
import numpy as np
import os

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")

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

def run_feature_engineering():
    print("=== Phase 2: Feature Engineering ===")
    
    # 1. Load cleaned data from Phase 1
    club_gameweek_path = os.path.join(data_dir, "club_player_gameweek.parquet")
    if not os.path.exists(club_gameweek_path):
        raise FileNotFoundError(f"Cleaned gameweek file not found at {club_gameweek_path}. Run clean_data.py first.")
    
    df_fpl = pd.read_parquet(club_gameweek_path)
    df_fpl['kickoff_time'] = pd.to_datetime(df_fpl['kickoff_time']).dt.tz_localize(None)
    
    # Load Understat player match logs
    pmd_path = os.path.join(workspace_dir, "player_match_data.csv")
    df_pmd = pd.read_csv(pmd_path)
    df_pmd['date'] = pd.to_datetime(df_pmd['date'])
    # Convert match date to end-of-day datetime to prevent leakage when merging with kickoff_time
    df_pmd['match_datetime'] = df_pmd['date'] + pd.Timedelta(hours=23, minutes=59, seconds=59)
    
    print(f"Loaded {len(df_fpl)} FPL gameweek rows and {len(df_pmd)} Understat match logs.")

    # 2. Determine Player's Team in Understat match logs
    # Create player-to-teams map from Understat season aggregates
    us_stats_path = os.path.join(workspace_dir, "league_player_stats.csv")
    us_stats = pd.read_csv(us_stats_path)
    player_teams = {}
    for idx, row in us_stats.iterrows():
        p_id = row['id']
        t_title = row['team_title']
        teams = [t.strip() for t in t_title.split(',')] if isinstance(t_title, str) else []
        if p_id not in player_teams:
            player_teams[p_id] = set()
        player_teams[p_id].update(teams)
        
    def get_player_team_in_match(row):
        p_id = row['player_id']
        h = row['h_team']
        a = row['a_team']
        teams = player_teams.get(p_id, set())
        if h in teams and a not in teams:
            return h
        elif a in teams and h not in teams:
            return a
        else:
            return h # default to home team
            
    df_pmd['player_team'] = df_pmd.apply(get_player_team_in_match, axis=1)
    df_pmd['opponent_team'] = np.where(df_pmd['player_team'] == df_pmd['h_team'], df_pmd['a_team'], df_pmd['h_team'])
    df_pmd['is_home'] = df_pmd['player_team'] == df_pmd['h_team']
    df_pmd['goals_conceded'] = np.where(df_pmd['is_home'], df_pmd['a_goals'], df_pmd['h_goals'])

    # 3. Precompute Match-Level Team Stats (for opponent difficulty)
    # Find xG conceded per team in each match by summing opponent players' xG
    # Group by match id, opponent_team
    opp_xg = df_pmd.groupby(['id', 'opponent_team'])['xG'].sum().reset_index()
    opp_xg = opp_xg.rename(columns={'opponent_team': 'team_conceding', 'xG': 'xG_conceded'})
    
    # We can also get goals conceded by the team
    team_goals_conceded = df_pmd[['id', 'opponent_team', 'goals_conceded']].drop_duplicates()
    team_goals_conceded = team_goals_conceded.rename(columns={'opponent_team': 'team_conceding'})
    
    team_match_stats = pd.merge(team_goals_conceded, opp_xg, on=['id', 'team_conceding'])
    
    # Merge date and season back in
    match_dates = df_pmd[['id', 'match_datetime', 'season']].drop_duplicates()
    team_match_stats = pd.merge(team_match_stats, match_dates, on='id')
    team_match_stats = team_match_stats.sort_values(by='match_datetime').reset_index(drop=True)
    
    print("Computed match-level team stats.")

    # 4. Compute Opponent Defensive Rolling Averages
    # We want to precompute rolling defensive stats for each team at each date
    team_match_stats['rolling_goals_conceded_5'] = team_match_stats.groupby(['team_conceding', 'season'])['goals_conceded'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    team_match_stats['rolling_xG_conceded_5'] = team_match_stats.groupby(['team_conceding', 'season'])['xG_conceded'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    team_match_stats['rolling_goals_conceded_10'] = team_match_stats.groupby(['team_conceding', 'season'])['goals_conceded'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    team_match_stats['rolling_xG_conceded_10'] = team_match_stats.groupby(['team_conceding', 'season'])['xG_conceded'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    
    # Fill NaNs with team average or global average
    team_match_stats = team_match_stats.fillna(0)

    # 5. Compute Player-Level Understat Rolling Stats
    # Sort logs chronologically within each player & season to reset at season boundary
    df_pmd = df_pmd.sort_values(by=['player_id', 'season', 'match_datetime']).reset_index(drop=True)
    
    # Precompute rolling sums for player match stats (shifted by 1 to exclude current match)
    for K in [3, 5, 10]:
        df_pmd[f'roll_xG_{K}'] = df_pmd.groupby(['player_id', 'season'])['xG'].transform(lambda x: x.shift(1).rolling(K, min_periods=1).sum())
        df_pmd[f'roll_xA_{K}'] = df_pmd.groupby(['player_id', 'season'])['xA'].transform(lambda x: x.shift(1).rolling(K, min_periods=1).sum())
        df_pmd[f'roll_npxG_{K}'] = df_pmd.groupby(['player_id', 'season'])['npxG'].transform(lambda x: x.shift(1).rolling(K, min_periods=1).sum())
        df_pmd[f'roll_time_{K}'] = df_pmd.groupby(['player_id', 'season'])['time'].transform(lambda x: x.shift(1).rolling(K, min_periods=1).sum())
        
        # Calculate per-90 rates
        df_pmd[f'xG90_{K}'] = np.where(df_pmd[f'roll_time_{K}'] > 0, df_pmd[f'roll_xG_{K}'] / df_pmd[f'roll_time_{K}'] * 90, 0)
        df_pmd[f'xA90_{K}'] = np.where(df_pmd[f'roll_time_{K}'] > 0, df_pmd[f'roll_xA_{K}'] / df_pmd[f'roll_time_{K}'] * 90, 0)
        df_pmd[f'npxG90_{K}'] = np.where(df_pmd[f'roll_time_{K}'] > 0, df_pmd[f'roll_npxG_{K}'] / df_pmd[f'roll_time_{K}'] * 90, 0)
        
    print("Precomputed player-level rolling stats.")

    # 6. Compute FPL-Level Player Minutes Trend
    # Sort FPL gameweek history chronologically
    df_fpl = df_fpl.sort_values(by=['element', 'round']).reset_index(drop=True)
    
    # Compute rolling average minutes (shifted by 1 to exclude current gameweek)
    df_fpl['fpl_roll_min_3'] = df_fpl.groupby('element')['minutes'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    df_fpl['fpl_roll_min_5'] = df_fpl.groupby('element')['minutes'].transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    
    # Rotation risk flag: minutes in last week was 0, but average in prior weeks was > 30
    df_fpl['fpl_prev_min_1'] = df_fpl.groupby('element')['minutes'].shift(1)
    df_fpl['fpl_prev_min_2'] = df_fpl.groupby('element')['minutes'].shift(2)
    df_fpl['rotation_risk'] = np.where((df_fpl['fpl_prev_min_1'] == 0) & (df_fpl['fpl_prev_min_2'] > 30), 1, 0)
    
    # Fill NaNs
    df_fpl['fpl_roll_min_3'] = df_fpl['fpl_roll_min_3'].fillna(0)
    df_fpl['fpl_roll_min_5'] = df_fpl['fpl_roll_min_5'].fillna(0)
    df_fpl['rotation_risk'] = df_fpl['rotation_risk'].fillna(0)

    # 7. Merge Player Rolling Stats with FPL Gameweeks using merge_asof
    # We will do this player-by-player to avoid massive memory usage and ensure correctness
    df_merged_list = []
    
    # Map FPL team to Understat team for joining opponent stats
    # Load FPL team names and map them
    fpl_teams_map = df_fpl[['opponent_team', 'was_home', 'team_name']].drop_duplicates().copy()
    
    # We want a clean map from opponent_team (FPL ID) to Understat team name
    # Let's map it via FPL players_master team mapping
    fpl_team_id_to_name = {
        1: 'Arsenal', 2: 'Aston Villa', 3: 'Bournemouth', 4: 'Brentford', 5: 'Brighton', 
        6: 'Burnley', 7: 'Chelsea', 8: 'Crystal Palace', 9: 'Everton', 10: 'Fulham', 
        11: 'Leeds', 12: 'Liverpool', 13: 'Man City', 14: 'Man Utd', 15: 'Newcastle', 
        16: "Nott'm Forest", 17: 'Spurs', 18: 'Sunderland', 19: 'West Ham', 20: 'Wolves'
    }
    
    def get_understat_team_name(fpl_team_id):
        fpl_name = fpl_team_id_to_name.get(fpl_team_id, "")
        return clean_team_name(fpl_name)

    # Now let's loop over players who have a matched understat_id
    print("Merging rolling features...")
    
    # Split FPL into matched and unmatched
    fpl_matched = df_fpl[df_fpl['understat_id'].notna()].copy()
    fpl_unmatched = df_fpl[df_fpl['understat_id'].isna()].copy()
    
    # For matched players, we merge_asof with their Understat match-level rolling stats
    matched_results = []
    for u_id, group in fpl_matched.groupby('understat_id'):
        p_pmd = df_pmd[df_pmd['player_id'] == u_id].copy()
        
        if len(p_pmd) == 0:
            # If no match logs found (e.g. newly registered), append group as-is with 0 features
            for K in [3, 5, 10]:
                group[f'xG90_{K}'] = 0.0
                group[f'xA90_{K}'] = 0.0
                group[f'npxG90_{K}'] = 0.0
            matched_results.append(group)
            continue
            
        # Sort both by datetime key
        group = group.sort_values(by='kickoff_time')
        p_pmd = p_pmd.sort_values(by='match_datetime')
        
        # merge_asof: match kickoff_time with the latest match_datetime before kickoff_time
        # allow_exact_matches=False is critical to prevent leaks if a game was played on the same minute (though match_datetime is end of day anyway)
        merged = pd.merge_asof(
            group,
            p_pmd[['match_datetime', 
                   'xG90_3', 'xA90_3', 'npxG90_3',
                   'xG90_5', 'xA90_5', 'npxG90_5',
                   'xG90_10', 'xA90_10', 'npxG90_10']],
            left_on='kickoff_time',
            right_on='match_datetime',
            direction='backward',
            allow_exact_matches=False
        )
        matched_results.append(merged)
        
    if matched_results:
        fpl_matched_merged = pd.concat(matched_results, ignore_index=True)
    else:
        fpl_matched_merged = pd.DataFrame()
        
    # For unmatched players, set Understat features to 0
    for K in [3, 5, 10]:
        fpl_unmatched[f'xG90_{K}'] = 0.0
        fpl_unmatched[f'xA90_{K}'] = 0.0
        fpl_unmatched[f'npxG90_{K}'] = 0.0
    fpl_unmatched['match_datetime'] = pd.NaT
    
    # Combine back
    df_combined = pd.concat([fpl_matched_merged, fpl_unmatched], ignore_index=True)
    df_combined = df_combined.sort_values(by=['element', 'round']).reset_index(drop=True)
    
    # 8. Join Opponent Difficulty Features
    # For each row, opponent team Understat name
    df_combined['opponent_understat_team'] = df_combined['opponent_team'].apply(get_understat_team_name)
    
    # We do a merge_asof for opponent defensive stats too!
    # This prevents any leaks for opponent stats
    opp_merged_list = []
    for team, group in df_combined.groupby('opponent_understat_team'):
        t_stats = team_match_stats[team_match_stats['team_conceding'] == team].copy()
        
        if len(t_stats) == 0:
            group['opp_goals_conceded_5'] = 1.2 # default sensible averages
            group['opp_xG_conceded_5'] = 1.2
            group['opp_goals_conceded_10'] = 1.2
            group['opp_xG_conceded_10'] = 1.2
            opp_merged_list.append(group)
            continue
            
        group = group.sort_values(by='kickoff_time')
        t_stats = t_stats.sort_values(by='match_datetime')
        
        merged = pd.merge_asof(
            group,
            t_stats[['match_datetime', 
                     'rolling_goals_conceded_5', 'rolling_xG_conceded_5',
                     'rolling_goals_conceded_10', 'rolling_xG_conceded_10']],
            left_on='kickoff_time',
            right_on='match_datetime',
            direction='backward',
            allow_exact_matches=False,
            suffixes=('', '_opp')
        )
        opp_merged_list.append(merged)
        
    df_final = pd.concat(opp_merged_list, ignore_index=True)
    df_final = df_final.sort_values(by=['element', 'round']).reset_index(drop=True)
    
    # Rename columns and fill NaNs
    df_final = df_final.rename(columns={
        'rolling_goals_conceded_5': 'opp_goals_conceded_5',
        'rolling_xG_conceded_5': 'opp_xG_conceded_5',
        'rolling_goals_conceded_10': 'opp_goals_conceded_10',
        'rolling_xG_conceded_10': 'opp_xG_conceded_10'
    })
    
    for col in ['opp_goals_conceded_5', 'opp_xG_conceded_5', 'opp_goals_conceded_10', 'opp_xG_conceded_10']:
        df_final[col] = df_final[col].fillna(1.2)

    # Fill set-piece fields NaNs with default high values (e.g. 4)
    for col in ['corners_and_indirect_freekicks_order', 'direct_freekicks_order', 'penalties_order']:
        df_final[col] = df_final[col].fillna(4)

    # 9. Create Target Variable (Shifted Next-Gameweek Points)
    # Target points for week W is total_points in week W+1
    df_final['target_points'] = df_final.groupby('element')['total_points'].shift(-1)
    
    # Drop rows where target_points is NaN (i.e. round 38)
    df_final = df_final.dropna(subset=['target_points']).reset_index(drop=True)
    
    # 10. Strict Leakage Verification
    print("=== Verification: Running Strict Leakage Check ===")
    leak_count = 0
    
    # For each row, check that the FPL gameweek kickoff_time is strictly greater than:
    # - The date of any match in Understat used to compute its features (match_datetime)
    # - The kickoff_time of any prior gameweek used to compute its rolling minutes
    
    # We can check this by verifying match_datetime < kickoff_time
    # Where match_datetime is the timestamp matched in merge_asof
    # Let's check both match_datetime and match_datetime_opp
    
    df_final['match_datetime'] = pd.to_datetime(df_final['match_datetime'])
    if 'match_datetime_opp' in df_final.columns:
        df_final['match_datetime_opp'] = pd.to_datetime(df_final['match_datetime_opp'])
        mask_leak = (df_final['match_datetime'] >= df_final['kickoff_time']) | (df_final['match_datetime_opp'] >= df_final['kickoff_time'])
    else:
        mask_leak = (df_final['match_datetime'] >= df_final['kickoff_time'])
        
    leak_count = mask_leak.sum()
    if leak_count > 0:
        leaked_rows = df_final[mask_leak]
        print(leaked_rows[['element', 'round', 'kickoff_time', 'match_datetime']].head(10))
        raise ValueError(f"CRITICAL ERROR: Data leakage detected in {leak_count} rows! Match logs occurred after gameweek kickoff.")
        
    print("  Leakage check passed! No future records used.")

    # 11. Save Features
    features_path = os.path.join(data_dir, "features.parquet")
    df_final.to_parquet(features_path, index=False)
    print(f"Features successfully saved to {features_path} ({len(df_final)} rows)")

if __name__ == "__main__":
    run_feature_engineering()
