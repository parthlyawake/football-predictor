import pandas as pd
import numpy as np
import os
import unicodedata
import re
import pulp
from scipy.optimize import minimize

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")

# Dictionary mapping FPL region codes to national team names in results.csv
region_to_team = {
    3: 'Algeria', 10: 'Argentina', 13: 'Australia', 14: 'Austria', 21: 'Belgium',
    30: 'Brazil', 39: 'Canada', 48: 'Colombia', 50: 'DR Congo', 54: 'Ivory Coast',
    57: 'Czech Republic', 62: 'Ecuador', 63: 'Egypt', 73: 'France', 80: 'Germany',
    81: 'Ghana', 97: 'Croatia', 98: 'Hungary', 106: 'Italy', 108: 'Japan',
    114: 'South Korea', 132: 'Mali', 139: 'Mexico', 145: 'Morocco', 152: 'Netherlands',
    154: 'New Zealand', 157: 'Nigeria', 161: 'Norway', 168: 'Paraguay', 172: 'Poland',
    173: 'Portugal', 189: 'Senegal', 190: 'Serbia', 195: 'Slovenia', 198: 'South Africa',
    200: 'Spain', 206: 'Sweden', 207: 'Switzerland', 218: 'Tunisia', 219: 'Turkey',
    225: 'Ukraine', 229: 'United States', 230: 'Uruguay', 231: 'Uzbekistan',
    241: 'England', 242: 'Northern Ireland', 243: 'Scotland', 244: 'Wales'
}

def normalize_name(name):
    if not isinstance(name, str):
        return ""
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

def run_track_b():
    print("=== Phase 4: Track B (World Cup 2026) Model and Optimizer ===")
    
    # 1. Load Parquet Clean Files
    results = pd.read_parquet(os.path.join(data_dir, "intl_team_match.parquet"))
    goalscorers = pd.read_parquet(os.path.join(data_dir, "intl_goalscorers.parquet"))
    shootouts = pd.read_parquet(os.path.join(data_dir, "intl_shootouts.parquet"))
    
    # Parse dates
    results['date'] = pd.to_datetime(results['date'])
    goalscorers['date'] = pd.to_datetime(goalscorers['date'])
    shootouts['date'] = pd.to_datetime(shootouts['date'])
    
    # 2. Simulate Elo Ratings
    print("Simulating international team Elo ratings...")
    elo = {}
    
    # Get tournament weights
    def get_match_weight(tournament):
        t_lower = tournament.lower()
        if 'fifa world cup' in t_lower and 'qualification' not in t_lower:
            return 60
        elif any(x in t_lower for x in ['euro', 'copa', 'nations cup', 'asian cup', 'gold cup']) and 'qualification' not in t_lower:
            return 40
        elif 'qualification' in t_lower or 'nations league' in t_lower:
            return 30
        elif 'friendly' in t_lower:
            return 20
        else:
            return 20
            
    # Chronological sort
    completed_matches = results.dropna(subset=['home_score', 'away_score']).sort_values('date').copy()
    upcoming_matches = results[results['home_score'].isna()].sort_values('date').copy()
    
    # We will record Elo at the time of each match to fit our Poisson model
    match_elo_history = []
    
    for idx, row in completed_matches.iterrows():
        h = row['home_team']
        a = row['away_team']
        
        # Initialize if not present
        if h not in elo: elo[h] = 1500.0
        if a not in elo: elo[a] = 1500.0
        
        r_h = elo[h]
        r_a = elo[a]
        
        # Save Elo before update
        match_elo_history.append({
            'id': idx,
            'h_elo': r_h,
            'a_elo': r_a,
            'elo_diff': r_h - r_a
        })
        
        # Calculate expected scores
        e_h = 1.0 / (1.0 + 10.0 ** ((r_a - r_h) / 400.0))
        e_a = 1.0 / (1.0 + 10.0 ** ((r_h - r_a) / 400.0))
        
        # Actual score
        hs = row['home_score']
        as_ = row['away_score']
        if hs > as_:
            s_h, s_a = 1.0, 0.0
        elif as_ > hs:
            s_h, s_a = 0.0, 1.0
        else:
            s_h, s_a = 0.5, 0.5
            
        K = get_match_weight(row['tournament'])
        
        # Update
        elo[h] = r_h + K * (s_h - e_h)
        elo[a] = r_a + K * (s_a - e_a)
        
    df_elo_hist = pd.DataFrame(match_elo_history)
    completed_matches = completed_matches.reset_index().rename(columns={'index': 'id'})
    completed_matches = pd.merge(completed_matches, df_elo_hist, on='id')
    
    print(f"Elo simulation finished. Top 10 rated teams:")
    sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
    for team, rating in sorted_elo[:10]:
        print(f"  - {team}: {rating:.1f}")
        
    # 3. Shootout Win Rates
    print("\nCalculating shootout win rates...")
    shootout_counts = {}
    shootout_wins = {}
    for idx, row in shootouts.iterrows():
        h = row['home_team']
        a = row['away_team']
        w = row['winner']
        
        shootout_counts[h] = shootout_counts.get(h, 0) + 1
        shootout_counts[a] = shootout_counts.get(a, 0) + 1
        shootout_wins[w] = shootout_wins.get(w, 0) + 1
        
    def get_shootout_win_rate(team):
        played = shootout_counts.get(team, 0)
        if played == 0:
            return 0.5
        return shootout_wins.get(team, 0) / played

    # 4. Fit Poisson Goals Model
    # Fit on completed matches from year 2010 onwards for modern accuracy
    df_fit = completed_matches[completed_matches['date'] >= '2010-01-01'].copy()
    
    # We want to fit:
    # lambda_home = exp(b0 + b1 * elo_diff + b2 * neutral)
    # lambda_away = exp(g0 - g1 * elo_diff + g2 * neutral)
    # Let's write a simple MLE solver
    def neg_log_likelihood(params, df_data, is_home):
        # params: [intercept, elo_diff_coef, neutral_coef]
        intercept, b_elo, b_neutral = params
        
        diff = df_data['elo_diff'].values
        neutral = df_data['neutral'].astype(float).values
        actual_goals = df_data['home_score'].values if is_home else df_data['away_score'].values
        
        # Calculate lambda
        if is_home:
            log_lambdas = intercept + b_elo * diff + b_neutral * neutral
        else:
            log_lambdas = intercept - b_elo * diff + b_neutral * neutral
            
        lambdas = np.exp(log_lambdas)
        
        # Poisson log-likelihood: sum( y * log(lambda) - lambda - log(y!) )
        # Negate for minimization
        nll = -np.sum(actual_goals * log_lambdas - lambdas)
        return nll

    print("Fitting Poisson expected goals model...")
    # Initial guess
    init_home = [0.2, 0.001, -0.1]
    init_away = [0.1, 0.001, -0.1]
    
    res_home = minimize(neg_log_likelihood, init_home, args=(df_fit, True), method='Nelder-Mead')
    res_away = minimize(neg_log_likelihood, init_away, args=(df_fit, False), method='Nelder-Mead')
    
    b0, b1, b2 = res_home.x
    g0, g1, g2 = res_away.x
    
    print(f"  Home Model: log(lambda_H) = {b0:.4f} + {b1:.6f}*EloDiff + {b2:.4f}*Neutral")
    print(f"  Away Model: log(lambda_A) = {g0:.4f} - {g1:.6f}*EloDiff + {g2:.4f}*Neutral")

    # 5. Expected Goals per Upcoming Fixture
    print("\nComputing expected goals for remaining World Cup fixtures:")
    upcoming_wc = upcoming_matches[upcoming_matches['tournament'] == 'FIFA World Cup'].copy()
    
    match_predictions = []
    active_wc_teams = set()
    
    for idx, row in upcoming_wc.iterrows():
        h = row['home_team']
        a = row['away_team']
        neutral = row['neutral']
        
        if h not in elo: elo[h] = 1500.0
        if a not in elo: elo[a] = 1500.0
        
        r_h = elo[h]
        r_a = elo[a]
        diff = r_h - r_a
        
        lambda_h = np.exp(b0 + b1 * diff + (b2 if neutral else 0.0))
        lambda_a = np.exp(g0 - g1 * diff + (g2 if neutral else 0.0))
        
        # Shootout win rate tiebreaker
        so_w_h = get_shootout_win_rate(h)
        so_w_a = get_shootout_win_rate(a)
        
        match_predictions.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'home_team': h,
            'away_team': a,
            'home_elo': r_h,
            'away_elo': r_a,
            'expected_goals_home': lambda_h,
            'expected_goals_away': lambda_a,
            'shootout_win_rate_home': so_w_h,
            'shootout_win_rate_away': so_w_a
        })
        
        active_wc_teams.add(h)
        active_wc_teams.add(a)
        
        print(f"  - {row['date'].strftime('%Y-%m-%d')}: {h} ({r_h:.0f}) vs {a} ({r_a:.0f}) -> Expected Goals: {lambda_h:.2f} - {lambda_a:.2f}")

    df_match_preds = pd.DataFrame(match_predictions)

    # 6. Player Name Matching & Historical Goals
    print("\nProcessing player-level statistics...")
    # Load Understat matched players with World Cup squads (Phase 4 V2)
    pm_path = os.path.join(data_dir, "players_master_wc_v2.csv")
    pm = pd.read_csv(pm_path)
    
    # Load world_cup_squads to get caps and identify starting keepers
    squads_path = os.path.join(data_dir, "world_cup_squads.csv")
    squads = pd.read_csv(squads_path)
    
    # Identify max-cap goalkeeper for each national team (the starting GK)
    squads_gks = squads[squads['position'] == 'GK'].copy()
    squads_gks['caps'] = pd.to_numeric(squads_gks['caps'], errors='coerce').fillna(0)
    max_cap_gk_idx = squads_gks.groupby('team')['caps'].idxmax()
    starter_gks = set(squads_gks.loc[max_cap_gk_idx, 'player_name'].unique())
    
    # Identify max-cap forward for each national team (the starting FW)
    squads_fws = squads[squads['position'] == 'FW'].copy()
    squads_fws['caps'] = pd.to_numeric(squads_fws['caps'], errors='coerce').fillna(0)
    max_cap_fw_idx = squads_fws.groupby('team')['caps'].idxmax()
    starter_fws = set(squads_fws.loc[max_cap_fw_idx, 'player_name'].unique())
    
    # Filter players who are eligible (present in official WC squads PDF)
    # and whose national team is playing in the 13 matches
    pm_active = pm[pm['wc_matched_team'].notna()].copy()
    pm_active['national_team'] = pm_active['wc_matched_team']
    pm_active = pm_active[pm_active['national_team'].isin(active_wc_teams)].copy()
    print(f"Found {len(pm_active)} eligible players named in official World Cup squads.")

    # Calculate player-level recency-weighted international goals from goalscorers.csv
    # Normalize goalscorer names
    goalscorers['norm_scorer'] = goalscorers['scorer'].apply(normalize_name)
    pm_active['norm_wc_name'] = pm_active['wc_matched_name'].apply(normalize_name)
    pm_active['norm_us_name'] = pm_active['player_name_us'].apply(normalize_name)
    
    # Today's date reference
    ref_date = pd.to_datetime("2026-07-01")
    
    # Calculate recency weight for each goal: e^-0.0005*days
    goalscorers['days_ago'] = (ref_date - goalscorers['date']).dt.days
    goalscorers['weight'] = np.exp(-0.0005 * goalscorers['days_ago'])
    
    # Sum weights per scorer
    weighted_goals_map = goalscorers.groupby('norm_scorer')['weight'].sum().to_dict()
    
    # Map to active players
    player_weighted_goals = {}
    for idx, row in pm_active.iterrows():
        p_id = row['understat_id']
        w_name = row['norm_wc_name']
        u_name = row['norm_us_name']
        
        g = 0.0
        if w_name in weighted_goals_map:
            g = weighted_goals_map[w_name]
        elif u_name and u_name in weighted_goals_map:
            g = weighted_goals_map[u_name]
        player_weighted_goals[p_id] = g
        
    pm_active['weighted_intl_goals'] = pm_active['understat_id'].map(player_weighted_goals).fillna(0.0)
    pm_active['intl_goals_per_90'] = (pm_active['weighted_intl_goals'] / 40.0) * (90.0 / 75.0)
    pm_active['intl_goals_per_90'] = pm_active['intl_goals_per_90'].clip(0.0, 1.0)
    
    # Blend goals per 90: 70% club form (recency weighted), 30% international
    pm_active['blended_npxG90'] = 0.7 * pm_active['rec_npxG90'] + 0.3 * pm_active['intl_goals_per_90']
    pm_active['club_xA90'] = pm_active['rec_xA90']
    pm_active['club_kp90'] = pm_active['rec_xA90'] * 1.5
    pm_active['club_shots90'] = pm_active['rec_npxG90'] * 4.0
    
    # Tackles per 90 proxy: Central/defensive midfielders get 2.0, attacking get 1.0
    pm_active['tackles_per_90'] = pm_active.apply(lambda r: 1.0 if (r['rec_npxG90'] + r['rec_xA90']) >= 0.3 else 2.0, axis=1)
    
    # Map positions
    pos_map = {'GK': 'Goalkeeper', 'DF': 'Defender', 'MF': 'Midfielder', 'FW': 'Forward'}
    pm_active['position'] = pm_active['wc_matched_position'].map(pos_map)
    
    # Map now_cost (scaled proxy price)
    pm_active['now_cost'] = (pm_active['proxy_price'] * 10).astype(int)
    
    # Fill NaN starts and caps
    pm_active['starts'] = pm_active['starts'].fillna(0.0)
    pm_active['caps'] = pm_active['wc_matched_caps'].fillna(0.0)

    # 8. Expected Points Calculation for each Player in their upcoming fixture
    print("\nCalculating expected player points for upcoming matches...")
    
    pm_active_avail = pm_active.copy()
    
    player_exp_points = []
    
    for idx, row in pm_active_avail.iterrows():
        p_id = row['understat_id']
        team = row['national_team']
        pos = row['position']
        cost = row['now_cost']
        starts = row['starts']
        caps = row['caps'] if not pd.isna(row['caps']) else 0.0
        
        # Starter probability check
        raw_prob = max(starts / 38.0, caps / 80.0)
        base_prob = min(max(raw_prob, 0.0), 1.0)
        intl_factor = min(caps / 15.0, 1.0)
        
        if pos == 'Goalkeeper':
            starter_prob = 1.0 if row['wc_matched_name'] in starter_gks else 0.0
        elif pos == 'Forward':
            is_primary = row['wc_matched_name'] in starter_fws
            starter_prob = base_prob * intl_factor * (1.0 if is_primary else 0.2)
        else:
            starter_prob = base_prob * intl_factor
            
        # Find the fixture for this team
        match_row = df_match_preds[(df_match_preds['home_team'] == team) | (df_match_preds['away_team'] == team)]
        if len(match_row) == 0:
            # Not playing in the 13 matches
            continue
            
        m = match_row.iloc[0]
        is_home = m['home_team'] == team
        
        exp_goals_for = m['expected_goals_home'] if is_home else m['expected_goals_away']
        exp_goals_against = m['expected_goals_away'] if is_home else m['expected_goals_home']
        
        # 1. Expected Minutes Points
        exp_min_points = 2.0 * starter_prob
        
        # 2. Expected Goal Points
        eg = row['blended_npxG90'] * (exp_goals_for / 1.3)
        if pos == 'Forward':
            exp_goal_points = (eg * 4.0 + eg * 0.10 * 1.0) * starter_prob
        elif pos == 'Midfielder':
            exp_goal_points = (eg * 5.0 + eg * 0.25 * 1.0) * starter_prob
        elif pos == 'Defender':
            exp_goal_points = (eg * 6.0 + eg * 0.10 * 1.0) * starter_prob
        else: # Goalkeeper
            exp_goal_points = (eg * 6.0) * starter_prob
            
        # 3. Expected Assist Points
        ea = row['club_xA90'] * (exp_goals_for / 1.3)
        exp_assist_points = (ea * 3.0) * starter_prob
        
        # 4. Expected Clean Sheet Points
        cs_prob = np.exp(-exp_goals_against)
        if pos in ['Goalkeeper', 'Defender']:
            exp_cs_points = (cs_prob * 5.0) * starter_prob
        elif pos == 'Midfielder':
            exp_cs_points = (cs_prob * 1.0) * starter_prob
        else:
            exp_cs_points = 0.0
            
        # 5. Expected Goals Conceded Penalty (GK/Defender only)
        if pos in ['Goalkeeper', 'Defender']:
            exp_gc_points = -(exp_goals_against - 1.0 + np.exp(-exp_goals_against)) * starter_prob
        else:
            exp_gc_points = 0.0
            
        # 6. Expected Tackles Points (Midfielders only: +1 point per 3 tackles)
        if pos == 'Midfielder':
            exp_tackles = row['tackles_per_90'] * (exp_goals_against / 1.3)
            exp_tackle_points = ((exp_tackles / 3.0) * 1.0) * starter_prob
        else:
            exp_tackle_points = 0.0
            
        # 7. Expected Chances Created Points (Midfielders only: +1 point per 2 chances created)
        if pos == 'Midfielder':
            exp_chances = row['club_kp90'] * (exp_goals_for / 1.3)
            exp_chance_points = ((exp_chances / 2.0) * 1.0) * starter_prob
        else:
            exp_chance_points = 0.0
            
        # 8. Expected Shots on Target Points (Forwards only: +1 point per 2 shots on target)
        if pos == 'Forward':
            exp_sot = 0.35 * row['club_shots90'] * (exp_goals_for / 1.3)
            exp_sot_points = ((exp_sot / 2.0) * 1.0) * starter_prob
        else:
            exp_sot_points = 0.0
            
        # 9. Expected Qualification Booster Points (+2 points if team advances to next round, weighted by probability)
        import math
        p_draw = 0.0
        p_home_win = 0.0
        p_away_win = 0.0
        for h_g in range(12):
            p_h = np.exp(-exp_goals_for) * (exp_goals_for**h_g) / math.factorial(h_g) if exp_goals_for > 0 else (1.0 if h_g == 0 else 0.0)
            for a_g in range(12):
                p_a = np.exp(-exp_goals_against) * (exp_goals_against**a_g) / math.factorial(a_g) if exp_goals_against > 0 else (1.0 if a_g == 0 else 0.0)
                p_cell = p_h * p_a
                if h_g > a_g:
                    p_home_win += p_cell
                elif h_g < a_g:
                    p_away_win += p_cell
                else:
                    p_draw += p_cell
        total_p = p_home_win + p_away_win + p_draw
        p_home_win /= total_p
        p_away_win /= total_p
        p_draw /= total_p
        
        so_w_home = m['shootout_win_rate_home']
        
        if is_home:
            adv_prob = p_home_win + p_draw * so_w_home
        else:
            adv_prob = p_away_win + p_draw * (1.0 - so_w_home)
            
        exp_qual_points = (2.0 * adv_prob) * starter_prob
            
        # Base expected points (scouting bonus disabled completely)
        exp_points = (exp_min_points + exp_goal_points + exp_assist_points + 
                      exp_cs_points + exp_gc_points + exp_tackle_points + 
                      exp_chance_points + exp_sot_points + exp_qual_points)
        
        player_exp_points.append({
            'understat_id': p_id,
            'player_name_us': row['player_name_us'],
            'team_name': team,
            'position': pos,
            'value': cost,
            'predicted_points': exp_points,
            'expected_goals_fixture': eg,
            'expected_assists_fixture': ea,
            'clean_sheet_prob': cs_prob,
            'starter_prob': starter_prob,
            'starts': starts,
            'caps': caps
        })
        
    df_opt = pd.DataFrame(player_exp_points)
    print(f"Calculated expected points for {len(df_opt)} players in upcoming fixtures.")
    
    # 9. Solve optimization problem using PuLP
    n_players = len(df_opt)
    prob = pulp.LpProblem("World_Cup_Knockout_Optimization", pulp.LpMaximize)
    
    # Variables
    squad_vars = [pulp.LpVariable(f"squad_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    starting_vars = [pulp.LpVariable(f"start_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    captain_vars = [pulp.LpVariable(f"captain_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    
    # Objective
    prob += pulp.lpSum([df_opt.loc[i, 'predicted_points'] * starting_vars[i] + 
                        df_opt.loc[i, 'predicted_points'] * captain_vars[i] for i in range(n_players)])
                        
    # Constraints
    prob += pulp.lpSum(squad_vars) == 15
    prob += pulp.lpSum([df_opt.loc[i, 'value'] * squad_vars[i] for i in range(n_players)]) <= 1050
    prob += pulp.lpSum(starting_vars) == 11
    prob += pulp.lpSum(captain_vars) == 1
    
    for i in range(n_players):
        prob += starting_vars[i] <= squad_vars[i]
        prob += captain_vars[i] <= starting_vars[i]
        
    # Positions
    positions = df_opt['position'].values
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Goalkeeper']) == 2
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Defender']) == 5
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Midfielder']) == 5
    prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if positions[i] == 'Forward']) == 3
    
    # Formations
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Goalkeeper']) == 1
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Defender']) >= 3
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Midfielder']) >= 2
    prob += pulp.lpSum([starting_vars[i] for i in range(n_players) if positions[i] == 'Forward']) >= 1
    
    # National team limits: Max 3 players per national team
    teams = df_opt['team_name'].values
    for team in np.unique(teams):
        prob += pulp.lpSum([squad_vars[i] for i in range(n_players) if teams[i] == team]) <= 3
        
    print("Solving World Cup squad optimization...")
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    if pulp.LpStatus[status] != "Optimal":
        print(f"WARNING: Optimization status is {pulp.LpStatus[status]}!")
        return
        
    squad_indices = [i for i in range(n_players) if squad_vars[i].varValue > 0.5]
    start_indices = [i for i in range(n_players) if starting_vars[i].varValue > 0.5]
    captain_index = [i for i in range(n_players) if captain_vars[i].varValue > 0.5][0]
    
    start_ex_cap = [i for i in start_indices if i != captain_index]
    vice_index = sorted(start_ex_cap, key=lambda i: df_opt.loc[i, 'predicted_points'], reverse=True)[0]
    
    df_squad = df_opt.loc[squad_indices].copy()
    df_squad['is_starting'] = df_squad.index.isin(start_indices)
    df_squad['is_captain'] = df_squad.index == captain_index
    df_squad['is_vice_captain'] = df_squad.index == vice_index
    
    import unicodedata
    def clean_name_ascii(s):
        if not isinstance(s, str):
            return ""
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')

    print("\n--- OPTIMAL WORLD CUP SQUAD SELECTED ---")
    print(f"Total Cost: L{df_squad['value'].sum()/10:.1f}m / L105.0m")
    
    print("\nStarting XI:")
    df_start = df_squad[df_squad['is_starting']].sort_values(by='position')
    for idx, row in df_start.iterrows():
        cap_str = " (C)" if row['is_captain'] else (" (VC)" if row['is_vice_captain'] else "")
        name = clean_name_ascii(row['player_name_us'])
        print(f"  [{row['position']}] {name} ({row['team_name']}) - Cost: L{row['value']/10:.1f}m, Exp Points: {row['predicted_points']:.2f}{cap_str}, StarterProb: {row['starter_prob']:.2f}, Caps: {row['caps']:.0f}, ClubStarts: {row['starts']}")
        print(f"    - Proxy metrics: Expected Goals: {row['expected_goals_fixture']:.3f}, Expected Assists: {row['expected_assists_fixture']:.3f}, Clean Sheet Prob: {row['clean_sheet_prob']:.1%}")
        
    print("\nBench:")
    df_bench = df_squad[~df_squad['is_starting']].sort_values(by='position')
    for idx, row in df_bench.iterrows():
        name = clean_name_ascii(row['player_name_us'])
        print(f"  [{row['position']}] {name} ({row['team_name']}) - Cost: L{row['value']/10:.1f}m, Exp Points: {row['predicted_points']:.2f}, StarterProb: {row['starter_prob']:.2f}, Caps: {row['caps']:.0f}, ClubStarts: {row['starts']}")
        
    # Save optimized World Cup squad
    opt_wc_path = os.path.join(data_dir, "optimized_wc_squad.csv")
    df_squad.to_csv(opt_wc_path, index=False)
    print(f"\nSaved optimized World Cup squad to {opt_wc_path}")
    print("\nAll tasks in Phase 4 completed successfully!")

if __name__ == "__main__":
    run_track_b()
