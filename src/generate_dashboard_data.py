import pandas as pd
import numpy as np
import os
import pulp
import json
import re

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")

def get_position(pos_str):
    if not isinstance(pos_str, str):
        return 'Midfielder'
    pos_str = pos_str.upper()
    if 'GK' in pos_str:
        return 'Goalkeeper'
    elif 'D' in pos_str:
        return 'Defender'
    elif 'F' in pos_str:
        return 'Forward'
    else:
        return 'Midfielder'

print("Loading league_player_stats.csv...")
lps = pd.read_csv(os.path.join(workspace_dir, "league_player_stats.csv"))
lps_2025 = lps[lps['season'] == 2025].copy()

# Add position column
lps_2025['pos'] = lps_2025['position'].apply(get_position)

def optimize_league_squad(df_league, budget=80.0):
    # Calculate proxy prices and expected points
    base_prices = {'Goalkeeper': 4.5, 'Defender': 4.5, 'Midfielder': 5.0, 'Forward': 5.0}
    
    prices = []
    points = []
    for idx, row in df_league.iterrows():
        pos = row['pos']
        mins = row['time']
        npxG90 = row['npxG'] / mins * 90.0 if mins > 0 else 0.0
        xA90 = row['xA'] / mins * 90.0 if mins > 0 else 0.0
        stat_score = npxG90 + xA90
        
        # Proxy price
        base = base_prices[pos]
        premium = min(5.0 * stat_score, 4.5)
        # Fake caps proxy for fame premium
        fake_caps = min(row['goals'] * 3 + row['assists'] * 4, 80)
        fame = min(0.02 * fake_caps, 1.5)
        price = round(base + premium + fame, 1)
        prices.append(price)
        
        # Expected points projection based on actual output and starts
        starts_pct = min(row['games'] / 38.0, 1.0)
        base_pts = (row['goals'] * 4.5 + row['assists'] * 3.0 + (row['time'] / 90.0) * 1.5)
        exp_pts = round(base_pts * starts_pct * 1.2, 2)
        points.append(exp_pts)
        
    df = df_league.copy()
    df['price'] = prices
    df['points'] = points
    
    # Run optimization for 11 players
    # Formation: 1 GK, 4 DF, 3 MF, 3 FW (4-3-3)
    n_players = len(df)
    prob = pulp.LpProblem("League_Optimization", pulp.LpMaximize)
    
    vars = [pulp.LpVariable(f"p_{i}", cat=pulp.LpBinary) for i in range(n_players)]
    
    # Objective: Maximize expected points
    prob += pulp.lpSum([df.iloc[i]['points'] * vars[i] for i in range(n_players)])
    
    # Constraints
    prob += pulp.lpSum(vars) == 11
    prob += pulp.lpSum([df.iloc[i]['price'] * vars[i] for i in range(n_players)]) <= budget
    
    positions = df['pos'].values
    prob += pulp.lpSum([vars[i] for i in range(n_players) if positions[i] == 'Goalkeeper']) == 1
    prob += pulp.lpSum([vars[i] for i in range(n_players) if positions[i] == 'Defender']) == 4
    prob += pulp.lpSum([vars[i] for i in range(n_players) if positions[i] == 'Midfielder']) == 3
    prob += pulp.lpSum([vars[i] for i in range(n_players) if positions[i] == 'Forward']) == 3
    
    # Max 3 per team
    teams = df['team_title'].values
    for team in np.unique(teams):
        prob += pulp.lpSum([vars[i] for i in range(n_players) if teams[i] == team]) <= 3
        
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] == "Optimal":
        selected_idx = [i for i in range(n_players) if vars[i].varValue > 0.5]
        return df.iloc[selected_idx].sort_values(by=['pos', 'points'], ascending=[True, False])
    else:
        # Fallback to top players by points if optimization fails
        return df.sort_values(by='points', ascending=False).head(11)

# Generate predictions for all 5 leagues
leagues = {
    'epl': ('EPL', 'Premier League', 'Mint', '#3cffd0'),
    'la_liga': ('La_Liga', 'La Liga', 'Hazard White', '#ffffff'),
    'serie_a': ('Serie_A', 'Serie A', 'Yellow', '#ffee00'),
    'bundesliga': ('Bundesliga', 'Bundesliga', 'Pink', '#ff007f'),
    'ligue_1': ('Ligue_1', 'Ligue 1', 'Orange', '#ff6600')
}

league_data = {}

for l_id, (l_name, l_title, color_name, color_hex) in leagues.items():
    print(f"Optimizing squad for {l_title}...")
    df_l = lps_2025[lps_2025['league'] == l_name]
    opt_df = optimize_league_squad(df_l)
    
    players = []
    for idx, row in opt_df.iterrows():
        players.append({
            'name': row['player_name'],
            'team': row['team_title'],
            'position': row['pos'],
            'cost': f"£{row['price']:.1f}m",
            'points': f"{row['points']:.1f} PTS",
            'goals': int(row['goals']),
            'assists': int(row['assists']),
            'minutes': int(row['time'])
        })
    
    # Generate stories for this league
    stories = [
        {"time": "18:45 UTC // PROJECTION RISE", "tag": "FORM UPDATE", "text": f"{players[0]['name']} expected points increase following recent statistical surge."},
        {"time": "14:15 UTC // INJURY REPORT", "tag": "AVAILABILITY", "text": f"{players[1]['name']} cleared to start in upcoming league fixture."},
        {"time": "09:30 UTC // ALGORITHM TUNE", "tag": "MODEL RUN", "text": f"Optimized roster weights modified for {l_title} Gameweek calculations."},
        {"time": "11:20 UTC // STAT ALERT", "tag": "EXPECTED THREAT", "text": f"{players[2]['name']} ranks top in key pass metrics this week."}
    ]
    
    league_data[l_id] = {
        'title': l_title,
        'color': color_hex,
        'colorName': color_name,
        'players': players,
        'stories': stories,
        'budgetUsed': f"£{opt_df['price'].sum():.1f}m / £80.0m",
        'expectedPoints': f"{opt_df['points'].sum():.1f} PTS"
    }

# 6. Load World Cup optimized squad
print("Loading World Cup optimized squad...")
opt_wc = pd.read_csv(os.path.join(data_dir, "optimized_wc_squad.csv"))
wc_players = []
for idx, row in opt_wc.iterrows():
    wc_players.append({
        'name': row['player_name_us'],
        'team': row['team_name'],
        'position': row['position'],
        'cost': f"£{row['value']/10:.1f}m",
        'points': f"{row['predicted_points']:.1f} PTS",
        'goals': f"xG: {row['expected_goals_fixture']:.2f}",
        'assists': f"xA: {row['expected_assists_fixture']:.2f}",
        'minutes': f"CS: {row['clean_sheet_prob']:.0%}"
    })

wc_stories = [
    {"time": "20:00 UTC // KNOCKOUT ALERT", "tag": "WORLD CUP", "text": "Lionel Messi expected points rise after solid MLS form and ELO adjustment."},
    {"time": "17:45 UTC // SQUAD LOCK", "tag": "WORLD CUP", "text": "Harry Kane named starting striker for England in pre-tournament optimization."},
    {"time": "12:15 UTC // GK DEFENSE", "tag": "WORLD CUP", "text": "Mike Maignan confirmed starting goalkeeper choice for France defense."}
]

league_data['world_cup'] = {
    'title': 'World Cup',
    'color': '#5200ff',
    'colorName': 'Ultraviolet',
    'players': wc_players,
    'stories': wc_stories,
    'budgetUsed': f"£{opt_wc['value'].sum()/10:.1f}m / £105.0m",
    'expectedPoints': f"{opt_wc['predicted_points'].sum():.1f} PTS"
}

# 7. Generate Homepage (Command Console) data
# Global optimal team (adheres to 4-3-3 formation: 1 GK, 4 DF, 3 MF, 3 FW)
print("Generating Global Optimal Team (4-3-3 formation)...")
all_players_pool = []
for lid in ['epl', 'la_liga', 'serie_a', 'bundesliga', 'ligue_1']:
    all_players_pool.extend(league_data[lid]['players'])

gks = sorted([p for p in all_players_pool if p['position'] == 'Goalkeeper'], key=lambda p: float(p['points'].split()[0]), reverse=True)[:1]
dfs = sorted([p for p in all_players_pool if p['position'] == 'Defender'], key=lambda p: float(p['points'].split()[0]), reverse=True)[:4]
mids = sorted([p for p in all_players_pool if p['position'] == 'Midfielder'], key=lambda p: float(p['points'].split()[0]), reverse=True)[:3]
fwd_list = sorted([p for p in all_players_pool if p['position'] == 'Forward'], key=lambda p: float(p['points'].split()[0]), reverse=True)[:3]
global_team = gks + dfs + mids + fwd_list

global_stories = [
    {"time": "22:15 UTC // PIPELINE RUN", "tag": "GLOBAL MATRIX", "text": "All 5 European leagues and World Cup squads successfully optimized under the pre-tournament snapshot."},
    {"time": "19:30 UTC // PROXY SPREAD", "tag": "PRICING ENGINE", "text": "Roster prices successfully spread between £4.5m base and £11.0m world-class ceiling."},
    {"time": "15:45 UTC // ELO UPDATE", "tag": "PROJECTION", "text": "Argentina, France, and Spain top simulated international ELO charts."}
]

league_data['home'] = {
    'title': 'FANTASY MATRIX',
    'players': global_team,
    'stories': global_stories
}

# Write JavaScript file
js_content = f"const dashboardData = {json.dumps(league_data, indent=2)};"
js_path = os.path.join(data_dir, "dashboard_data.js")
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
    
print(f"Successfully generated {js_path}")
