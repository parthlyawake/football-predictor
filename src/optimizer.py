import pandas as pd
import numpy as np
import os
import pulp

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(workspace_dir, "data")

def optimize_gameweek(round_num=30):
    print(f"\n=== Phase 3: Optimizing Gameweek {round_num} ===")
    
    predictions_path = os.path.join(data_dir, "predictions.parquet")
    if not os.path.exists(predictions_path):
        raise FileNotFoundError(f"Predictions file not found at {predictions_path}. Run train_predict.py first.")
        
    df = pd.read_parquet(predictions_path)
    
    # Filter for the target gameweek (the week we are predicting points for, which is round_num + 1)
    # Wait, the predictions.parquet contains rows where round = W, and target_points is points in week W+1
    # So if we want to optimize for gameweek W+1, we use features and predicted_points from round W!
    df_gw = df[df['round'] == round_num].copy()
    if len(df_gw) == 0:
        print(f"No records found for round {round_num}. Using the latest available round instead.")
        latest_round = df['round'].max()
        df_gw = df[df['round'] == latest_round].copy()
        round_num = latest_round
        
    print(f"Total players in round {round_num} prediction: {len(df_gw)}")
    
    # 1. Apply Availability and Injury Filters
    # FPL status: 'a' = available, 'i' = injured, 'd' = doubtful, 'u' = unavailable, 's' = suspended
    print("Applying availability filter...")
    df_avail = df_gw[df_gw['status'] == 'a'].copy()
    # Handle chance_of_playing_next_round: if NaN, assume 100%. If present, must be >= 50%
    df_avail = df_avail[(df_avail['chance_of_playing_next_round'].isna()) | (df_avail['chance_of_playing_next_round'] >= 50)].copy()
    print(f"  Players available after filtering: {len(df_avail)}")
    
    if len(df_avail) < 15:
        raise ValueError("Not enough available players to select a squad of 15!")
        
    # Reset index for pulp matching
    df_avail = df_avail.reset_index(drop=True)
    n_players = len(df_avail)
    
    # Define optimization variables
    prob = pulp.LpProblem("FPL_Optimization", pulp.LpMaximize)
    
    # Binary variables
    squad_vars = [pulp.LpVariable(f"squad_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    starting_vars = [pulp.LpVariable(f"start_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    captain_vars = [pulp.LpVariable(f"captain_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    
    # 2. Objective Function: Maximize starting XI points + captain bonus points
    # (Effectively starting XI points where captain is weighted twice)
    prob += pulp.lpSum([df_avail.loc[i, 'predicted_points'] * starting_vars[i] + 
                        df_avail.loc[i, 'predicted_points'] * captain_vars[i] for i in range(n_players)])
                        
    # 3. Constraints
    # Squad constraints
    prob += pulp.lpSum(squad_vars) == 15
    
    # Budget constraint (value is in tenths of a million, e.g. 55 = £5.5m. Total budget = 1000 = £100m)
    prob += pulp.lpSum([df_avail.loc[i, 'value'] * squad_vars[i] for i in range(n_players)]) <= 1000
    
    # Starting XI constraints
    prob += pulp.lpSum(starting_vars) == 11
    
    # Captain constraints
    prob += pulp.lpSum(captain_vars) == 1
    
    # Relational constraints
    for i in range(n_players):
        # Starting player must be in squad
        prob += starting_vars[i] <= squad_vars[i]
        # Captain must be in starting XI
        prob += captain_vars[i] <= starting_vars[i]
        
    # Position constraints
    positions = df_avail['position'].values
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Goalkeeper']) == 2
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Defender']) == 5
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Midfielder']) == 5
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Forward']) == 3
    
    # Starting XI formation constraints
    # Minimums: 1 GK, 3 DEF, 2 MID, 1 FWD
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Goalkeeper']) == 1
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Defender']) >= 3
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Midfielder']) >= 2
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Forward']) >= 1
    
    # Club constraints: Max 3 players from any single team
    teams = df_avail['team_name'].values
    for team in np.unique(teams):
        prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if teams[i] == team]) <= 3
        
    # Solve
    print("Solving the IP model...")
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    if pulp.LpStatus[status] != "Optimal":
        print(f"WARNING: Optimization status is {pulp.LpStatus[status]}!")
        return None
        
    # Parse results
    squad_indices = [i for i in range(n_players) if squad_vars[i].varValue > 0.5]
    start_indices = [i for i in range(n_players) if starting_vars[i].varValue > 0.5]
    captain_index = [i for i in range(n_players) if captain_vars[i].varValue > 0.5][0]
    
    # Get vice-captain (starting XI player with highest predicted points, excluding captain)
    start_ex_cap = [i for i in start_indices if i != captain_index]
    vice_index = sorted(start_ex_cap, key=lambda i: df_avail.loc[i, 'predicted_points'], reverse=True)[0]
    
    # Build tables
    df_squad = df_avail.loc[squad_indices].copy()
    df_squad['is_starting'] = df_squad.index.isin(start_indices)
    df_squad['is_captain'] = df_squad.index == captain_index
    df_squad['is_vice_captain'] = df_squad.index == vice_index
    
    print("\n--- OPTIMAL SQUAD SELECTED ---")
    print(f"Total Cost: £{df_squad['value'].sum()/10:.1f}m / £100.0m")
    
    # Display Starting XI
    print("\nStarting XI:")
    df_start = df_squad[df_squad['is_starting']].sort_values(by='position')
    for idx, row in df_start.iterrows():
        cap_str = " (C)" if row['is_captain'] else (" (VC)" if row['is_vice_captain'] else "")
        print(f"  [{row['position']}] {row['first_name']} {row['second_name']} ({row['team_name']}) - Cost: £{row['value']/10:.1f}m, Pred Points: {row['predicted_points']:.2f}{cap_str}")
        
    # Display Bench
    print("\nBench:")
    df_bench = df_squad[~df_squad['is_starting']].sort_values(by='position')
    for idx, row in df_bench.iterrows():
        print(f"  [{row['position']}] {row['first_name']} {row['second_name']} ({row['team_name']}) - Cost: £{row['value']/10:.1f}m, Pred Points: {row['predicted_points']:.2f}")
        
    # Verify starting XI conforms to constraints
    gks = len(df_start[df_start['position'] == 'Goalkeeper'])
    defs = len(df_start[df_start['position'] == 'Defender'])
    mids = len(df_start[df_start['position'] == 'Midfielder'])
    fwds = len(df_start[df_start['position'] == 'Forward'])
    
    print(f"\nFormation check: {defs}-{mids}-{fwds} ({gks} GK)")
    assert gks == 1, "Must have exactly 1 GK starting!"
    assert defs >= 3 and defs <= 5, f"Invalid number of defenders starting: {defs}!"
    assert mids >= 2 and mids <= 5, f"Invalid number of midfielders starting: {mids}!"
    assert fwds >= 1 and fwds <= 3, f"Invalid number of forwards starting: {fwds}!"
    print("SUCCESS: Starting XI formation constraints verified!")
    
    # Save optimized squad to CSV
    opt_path = os.path.join(data_dir, f"optimized_squad_gw{round_num}.csv")
    df_squad.to_csv(opt_path, index=False)
    print(f"Saved optimized squad to {opt_path}")
    
    return df_squad

if __name__ == "__main__":
    optimize_gameweek(30)
