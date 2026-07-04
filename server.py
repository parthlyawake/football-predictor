import pandas as pd
import numpy as np
import os
import pulp
import json
import urllib.parse as urlparse
from http.server import SimpleHTTPRequestHandler, HTTPServer
import sys
import re
import unicodedata

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")

def name_tokens(s):
    if not isinstance(s, str):
        return set()
    s = s.lower()
    s = s.replace('\ufffd', 'e')
    s = s.replace('ß', 'ss')
    s = s.replace('ue', 'u').replace('ae', 'a').replace('oe', 'o')
    s = s.replace("&#039;", "")
    s = s.replace("'", "")
    # strip accents
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    
    # split words
    words = re.findall(r'[a-z0-9]+', s)
    
    # Merge single letter O with next word (e.g. o reilly -> oreilly)
    merged_words = []
    i = 0
    while i < len(words):
        if words[i] == 'o' and i + 1 < len(words):
            merged_words.append('o' + words[i+1])
            i += 2
        else:
            merged_words.append(words[i])
            i += 1
            
    # Nickname expansions
    if 'nicolas' in merged_words and 'nico' not in merged_words:
        merged_words.append('nico')
    elif 'nico' in merged_words and 'nicolas' not in merged_words:
        merged_words.append('nicolas')
        
    return set(merged_words)

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

def check_player_match_us(name_us, sq_name):
    tokens_us = name_tokens(name_us)
    tokens_scorer = name_tokens(sq_name)
    intersect_us = tokens_scorer & tokens_us
    
    if len(intersect_us) == 0:
        return False
        
    min_tokens = min(len(tokens_us), len(tokens_scorer))
    if min_tokens >= 2:
        return len(intersect_us) >= 2
    else:
        return len(intersect_us) >= min_tokens

def check_player_match(name_us, wc_name, scorer_name):
    return check_player_match_us(name_us, scorer_name) or check_player_match_us(wc_name, scorer_name)

def assign_real_wc_price(row):
    pos = row['pos']
    name = str(row['player_name_us']).lower()
    wc_name = str(row['wc_matched_name']).lower()
    
    # Absolute Elite Overrides
    if 'mbappe' in name or 'mbappe' in wc_name: return 10.5
    if 'messi' in name or 'messi' in wc_name: return 11.0
    if 'kane' in name or 'kane' in wc_name: return 10.5
    if 'haaland' in name or 'haaland' in wc_name: return 10.5
    if 'vinicius' in name or 'vinicius' in wc_name: return 10.0
    if 'yamal' in name or 'yamal' in wc_name: return 8.5
    if 'bellingham' in name or 'bellingham' in wc_name: return 9.5
    if 'musiala' in name or 'musiala' in wc_name: return 9.5
    if 'saka' in name or 'saka' in wc_name: return 9.5
    if 'lukaku' in name or 'lukaku' in wc_name: return 7.4
    if 'merino' in name or 'merino' in wc_name: return 6.2
    
    # Positional Rule-Based Fallbacks for the Rest of the 1,200 Players
    caps = row['wc_matched_caps'] if not pd.isna(row['wc_matched_caps']) else 0.0
    starts = row['starts'] if not pd.isna(row['starts']) else 0.0
    
    if pos == 'Goalkeeper':
        return 5.5 if caps >= 50 else (4.6 if caps >= 15 else 3.8)
    elif pos == 'Defender':
        return 6.5 if starts >= 28 else (5.2 if starts >= 12 else 4.3)
    elif pos == 'Midfielder':
        return 8.0 if starts >= 25 else (6.5 if starts >= 10 else 5.0)
    elif pos == 'Forward':
        return 9.0 if starts >= 24 else (7.5 if starts >= 10 else 6.0)
    return 5.0

# 1. World Cup Expected Points Calculator (Replicating ELO & Poisson from track_b_model.py)
def calculate_wc_expected_points():
    # Load data
    results = pd.read_csv(os.path.join(workspace_dir, "results.csv"))
    shootouts = pd.read_csv(os.path.join(workspace_dir, "shootouts.csv"))
    squads = pd.read_csv(os.path.join(data_dir, "world_cup_squads.csv"))
    pm = pd.read_csv(os.path.join(data_dir, "players_master_wc_v2.csv"))
    gs = pd.read_csv(os.path.join(workspace_dir, "goalscorers.csv"))
    
    # Calculate goals scored in World Cup 2026 (since June 11, 2026)
    wc_goals = gs[(gs['date'] >= '2026-06-11') & (gs['own_goal'] == False)]
    wc_goals_counts = wc_goals['scorer'].value_counts().to_dict()
    
    # Identify FWs starters (GKs starts are dynamic now)
    squads_fws = squads[squads['position'] == 'FW'].copy()
    squads_fws['caps'] = pd.to_numeric(squads_fws['caps'], errors='coerce').fillna(0)
    max_cap_fw_idx = squads_fws.groupby('team')['caps'].idxmax()
    starter_fws = set(squads_fws.loc[max_cap_fw_idx, 'player_name'].unique())
    
    # Elo simulation
    elo = {}
    for team in squads['team'].unique():
        elo[team] = 1600.0
    elo['Argentina'] = 1950.0
    elo['France'] = 1920.0
    elo['Spain'] = 1920.0
    elo['England'] = 1880.0
    elo['Brazil'] = 1880.0
    elo['Belgium'] = 1820.0
    elo['Portugal'] = 1820.0
    
    # Simulate past matches to update Elo
    wc_past = results[(results['tournament'] == 'FIFA World Cup') & (results['date'] < '2026-06-28')].copy()
    for idx, row in wc_past.iterrows():
        t1, t2 = row['home_team'], row['away_team']
        if t1 not in elo: elo[t1] = 1600.0
        if t2 not in elo: elo[t2] = 1600.0
        r1, r2 = elo[t1], elo[t2]
        e1 = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / 400.0))
        e2 = 1.0 - e1
        s1 = 1.0 if row['home_score'] > row['away_score'] else (0.0 if row['home_score'] < row['away_score'] else 0.5)
        elo[t1] += 40.0 * (s1 - e1)
        elo[t2] += 40.0 * ((1.0 - s1) - e2)
        
    # Get upcoming fixtures (NaN scores in results.csv from June 28)
    wc_upcoming = results[(results['tournament'] == 'FIFA World Cup') & (results['date'] >= '2026-06-28') & (results['home_score'].isna())].copy()
    active_wc_teams = set(wc_upcoming['home_team'].unique()) | set(wc_upcoming['away_team'].unique())
    
    # Expected goals Poisson parameters
    match_predictions = []
    for idx, row in wc_upcoming.iterrows():
        h, a = row['home_team'], row['away_team']
        if h not in elo: elo[h] = 1600.0
        if a not in elo: elo[a] = 1600.0
        r_h, r_a = elo[h], elo[a]
        elo_diff = r_h - r_a
        
        lambda_h = np.exp(0.3530 + 0.002268 * elo_diff - 0.0692 * True)
        lambda_a = np.exp(-0.0468 - 0.002408 * elo_diff + 0.2655 * True)
        
        so_w_home = 0.5
        match_predictions.append({
            'home_team': h,
            'away_team': a,
            'expected_goals_home': lambda_h,
            'expected_goals_away': lambda_a,
            'shootout_win_rate_home': so_w_home
        })
    df_match_preds = pd.DataFrame(match_predictions)
    
    # Calculate player points
    pm_active = pm[pm['wc_matched_team'].notna()].copy()
    pm_active['national_team'] = pm_active['wc_matched_team']
    pm_active = pm_active[pm_active['national_team'].isin(active_wc_teams)].copy()
    
    # Hard-filter and remove players with fewer than 450 mins or fewer than 3 starts/caps
    pm_active = pm_active[(pm_active['time'] >= 450) | (pm_active['starts'] >= 3) | (pm_active['wc_matched_caps'] >= 3)].copy()
    
    # Map positions
    pos_map = {'GK': 'Goalkeeper', 'DF': 'Defender', 'MF': 'Midfielder', 'FW': 'Forward'}
    pm_active['pos'] = pm_active['wc_matched_position'].map(pos_map)
    
    # Hardcode positional overrides for hybrid wingers/midfielders
    for idx, row in pm_active.iterrows():
        p_name = str(row['player_name_us']).lower()
        wc_n = str(row['wc_matched_name']).lower()
        if 'dembele' in p_name or 'dembele' in wc_n or 'vinicius' in p_name or 'vinicius' in wc_n or 'yamal' in p_name or 'yamal' in wc_n or 'olise' in p_name or 'olise' in wc_n:
            pm_active.at[idx, 'pos'] = 'Midfielder'
            
    # Strict World Cup Squad List Gate: Roster Validation
    valid_indices = []
    for idx, row in pm_active.iterrows():
        name_us = row['player_name_us']
        team = row['national_team']
        
        squad_team = squads[squads['team'] == team]
        matched = False
        for _, s_row in squad_team.iterrows():
            sq_name = s_row['player_name']
            if check_player_match_us(name_us, sq_name):
                matched = True
                break
        if matched:
            valid_indices.append(idx)
            
    pm_active = pm_active.loc[valid_indices].copy()
            
    # Dynamic pricing normalization using assign_real_wc_price
    pm_active['price'] = pm_active.apply(assign_real_wc_price, axis=1)
    
    # Inject missing goalkeepers from non-top-5 leagues
    missing_gks = [
        {
            'understat_id': 99901, 'player_name_us': 'Diogo Costa', 'wc_matched_name': 'DIOGO COSTA',
            'wc_matched_team': 'Portugal', 'wc_matched_position': 'GK', 'wc_matched_caps': 46.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'FC Porto (POR)', 'league': 'Primeira Liga',
            'team_title': 'Portugal', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 5.2, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Portugal', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99902, 'player_name_us': 'Yassine Bounou', 'wc_matched_name': 'BOUNOU Yassine',
            'wc_matched_team': 'Morocco', 'wc_matched_position': 'GK', 'wc_matched_caps': 65.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Al Hilal SC (KSA)', 'league': 'Saudi Pro League',
            'team_title': 'Morocco', 'npxG': 0.0, 'xA': 0.0, 'time': 2700.0, 'games': 30.0,
            'starts': 30.0, 'price': 5.2, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Morocco', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99903, 'player_name_us': 'Camilo Vargas', 'wc_matched_name': 'VARGAS Camilo',
            'wc_matched_team': 'Colombia', 'wc_matched_position': 'GK', 'wc_matched_caps': 55.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Atlas FC (MEX)', 'league': 'Liga MX',
            'team_title': 'Colombia', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 5.2, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Colombia', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99904, 'player_name_us': 'Maxime Crepeau', 'wc_matched_name': 'CREPEAU Maxime',
            'wc_matched_team': 'Canada', 'wc_matched_position': 'GK', 'wc_matched_caps': 22.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Orlando City SC (USA)', 'league': 'MLS',
            'team_title': 'Canada', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 4.8, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Canada', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99905, 'player_name_us': 'Dominik Livakovic', 'wc_matched_name': 'LIVAKOVIC Dominik',
            'wc_matched_team': 'Croatia', 'wc_matched_position': 'GK', 'wc_matched_caps': 54.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'GNK Dinamo Zagreb (CRO)', 'league': 'Super Lig',
            'team_title': 'Croatia', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 5.2, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Croatia', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99906, 'player_name_us': 'Kasper Schmeichel', 'wc_matched_name': 'SCHMEICHEL Kasper',
            'wc_matched_team': 'Denmark', 'wc_matched_position': 'GK', 'wc_matched_caps': 105.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Celtic', 'league': 'Scottish Premiership',
            'team_title': 'Denmark', 'npxG': 0.0, 'xA': 0.0, 'time': 3420.0, 'games': 38.0,
            'starts': 38.0, 'price': 5.0, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Denmark', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99907, 'player_name_us': 'Gatito Fernandez', 'wc_matched_name': 'FERNANDEZ Gatito',
            'wc_matched_team': 'Paraguay', 'wc_matched_position': 'GK', 'wc_matched_caps': 18.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Cerro Porteño (PAR)', 'league': 'Serie A (Brazil)',
            'team_title': 'Paraguay', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 4.8, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Paraguay', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99908, 'player_name_us': 'Vozinha', 'wc_matched_name': 'VOZINHA',
            'wc_matched_team': 'Cape Verde', 'wc_matched_position': 'GK', 'wc_matched_caps': 65.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'GD Chaves (POR)', 'league': 'Slovak Super Liga',
            'team_title': 'Cape Verde', 'npxG': 0.0, 'xA': 0.0, 'time': 2700.0, 'games': 30.0,
            'starts': 30.0, 'price': 4.5, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Cape Verde', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99909, 'player_name_us': 'Lionel Mpasi', 'wc_matched_name': 'MPASI Lionel',
            'wc_matched_team': 'DR Congo', 'wc_matched_position': 'GK', 'wc_matched_caps': 15.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Le Havre AC (FRA)', 'league': 'Ligue 2',
            'team_title': 'DR Congo', 'npxG': 0.0, 'xA': 0.0, 'time': 2700.0, 'games': 30.0,
            'starts': 30.0, 'price': 4.5, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'DR Congo', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99910, 'player_name_us': 'Lawrence Ati-Zigi', 'wc_matched_name': 'ZIGI Lawrence Ati',
            'wc_matched_team': 'Ghana', 'wc_matched_position': 'GK', 'wc_matched_caps': 22.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'FC St. Gallen (SUI)', 'league': 'Swiss Super League',
            'team_title': 'Ghana', 'npxG': 0.0, 'xA': 0.0, 'time': 3240.0, 'games': 36.0,
            'starts': 36.0, 'price': 4.8, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Ghana', 'pos': 'Goalkeeper'
        },
        {
            'understat_id': 99911, 'player_name_us': 'Anatoliy Trubin', 'wc_matched_name': 'TRUBIN Anatoliy',
            'wc_matched_team': 'Ukraine', 'wc_matched_position': 'GK', 'wc_matched_caps': 17.0,
            'wc_matched_goals': 0.0, 'wc_matched_club': 'Benfica', 'league': 'Primeira Liga',
            'team_title': 'Ukraine', 'npxG': 0.0, 'xA': 0.0, 'time': 3060.0, 'games': 34.0,
            'starts': 34.0, 'price': 5.0, 'rec_npxG90': 0.0, 'rec_xA90': 0.0,
            'national_team': 'Ukraine', 'pos': 'Goalkeeper'
        }
    ]
    df_missing = pd.DataFrame(missing_gks)
    pm_active = pd.concat([pm_active, df_missing], ignore_index=True)
    
    # Pre-calculate max GK caps for dynamic starting hierarchy
    gk_players = pm_active[pm_active['pos'] == 'Goalkeeper'].copy()
    max_gk_caps = gk_players.groupby('national_team')['wc_matched_caps'].max().to_dict()
    
    player_exp_points = []
    for idx, row in pm_active.iterrows():
        p_id = row['understat_id']
        team = row['national_team']
        pos = row['pos']
        starts = row['starts'] if not pd.isna(row['starts']) else 0.0
        caps = row['wc_matched_caps'] if not pd.isna(row['wc_matched_caps']) else 0.0
        wc_name = row['wc_matched_name']
        name_us = row['player_name_us']
        
        # Fuzzy match for in-tournament goals count using name tokens
        wc_goals_count = 0
        tokens_us = name_tokens(name_us)
        tokens_wc = name_tokens(wc_name)
        for scorer, count in wc_goals_counts.items():
            tokens_scorer = name_tokens(scorer)
            if len(tokens_scorer & tokens_wc) >= 1 or len(tokens_scorer & tokens_us) >= 1:
                wc_goals_count = max(wc_goals_count, count)
                
        # Injury check
        injured_players = {
            'NEYMAR JR', 'NEYMAR', 'Neymar Jr', 'Neymar',
            'Frenkie de Jong', 'Gavi', 'David Alaba', 'Harry Maguire',
            'Teun Koopmeiners', 'Sven Botman'
        }
        is_injured = False
        for injured in injured_players:
            if injured.lower() in wc_name.lower() or injured.lower() in name_us.lower():
                is_injured = True
                break
                
        # Starter probability check
        wc_actual_starts = {
            'Lionel Messi': 1.0, 'Emiliano Martinez': 1.0, 'Nahuel Molina': 1.0, 
            'Lisandro Martinez': 1.0, 'Alexis Mac Allister': 1.0, 'Enzo Fernandez': 1.0,
            'Julian Alvarez': 0.5, 'Lautaro Martinez': 0.5, 'Nicolas Gonzalez': 0.0,
            'Nico Paz': 0.0, 'Giovani Lo Celso': 0.0,
            'Kylian Mbappe-Lottin': 1.0, 'Mike Maignan': 1.0, 'Jules Kounde': 1.0,
            'William Saliba': 1.0, 'Ousmane Dembele': 1.0, 'Michael Olise': 1.0,
            'Bradley Barcola': 1.0, 'Malo Gusto': 0.0, 'Desire Doue': 0.0, 'Mathis Cherki': 0.0,
            'Harry Kane': 1.0, 'Jordan Pickford': 1.0, 'Jude Bellingham': 1.0,
            'Nico O\'Reilly': 0.75, 'Morgan Rogers': 0.25, 'John Stones': 1.0,
            'Marc Cucurella': 1.0, 'Pedro Porro': 1.0, 'Pau Cubarsi': 1.0,
            'Aymeric Laporte': 1.0, 'Lamine Yamal': 1.0, 'Mikel Oyarzabal': 1.0,
            'Mikel Merino': 0.0, 'Alex Grimaldo': 0.0, 'Alex Baena': 0.0, 'Victor Munoz': 0.0,
            'Thibaut Courtois': 1.0, 'Maxim De Cuyper': 1.0, 'Youri Tielemans': 1.0,
            'Kevin De Bruyne': 1.0, 'Romelu Lukaku': 0.25, 'Leandro Trossard': 0.0,
            'Matias Fernandez-Pardo': 0.0, 'Alexis Saelemaekers': 0.0,
            'Alisson': 1.0, 'Gabriel Magalhaes': 1.0, 'Marquinhos': 1.0, 'Casemiro': 1.0,
            'Vinicius Junior': 1.0, 'Matheus Cunha': 1.0, 'Gabriel Martinelli': 0.0, 'Raphinha': 0.0,
            'Nuno Mendes': 1.0, 'Bruno Fernandes': 1.0, 'Cristiano Ronaldo': 1.0, 'Erling Haaland': 1.0,
            'Johan Mojica': 1.0, 'Luis Diaz': 1.0, 'Jhon Arias': 1.0,
            'Nico Elvedi': 1.0, 'Johan Manzambi': 1.0, 'Breel Embolo': 1.0, 'Granit Xhaka': 1.0,
            'Achraf Hakimi': 1.0, 'Brahim Diaz': 1.0, 'Alvaro Fidalgo': 0.0, 'Obed Vargas': 0.0,
            # Goalkeepers starting hierarchy
            'Diogo Costa': 1.0, 'Jose Sa': 0.0, 'Rui Silva': 0.0,
            'Yassine Bounou': 1.0, 'Camilo Vargas': 1.0, 'Maxime Crepeau': 1.0,
            'Dominik Livakovic': 1.0, 'Gatito Fernandez': 1.0, 'Vozinha': 1.0,
            'Lionel Mpasi': 1.0, 'Lawrence Ati-Zigi': 1.0, 'Anatoliy Trubin': 1.0,
            'Senne Lammens': 0.0, 'Mike Penders': 0.0, 'Dean Henderson': 0.0,
            'James Trafford': 0.0, 'David Raya': 0.0, 'Joan Garcia': 0.0,
            'Juan Musso': 0.0, 'Geronimo Rulli': 0.0, 'Robin Roefs': 0.0,
            'Mark Flekken': 0.0, 'Manuel Neuer': 0.0, 'Alexander Nubel': 0.0,
            'Mory Diaw': 0.0
        }
        
        matched_starts = None
        for key_name, start_val in wc_actual_starts.items():
            if check_player_match_us(name_us, key_name) or check_player_match_us(wc_name, key_name):
                matched_starts = start_val
                break
                
        raw_prob = max(starts / 38.0, caps / 80.0)
        base_prob = min(max(raw_prob, 0.0), 1.0)
        intl_factor = min(caps / 15.0, 1.0)
        
        if is_injured:
            starter_prob = 0.0
        elif matched_starts is not None:
            starter_prob = matched_starts
        elif pos == 'Goalkeeper':
            max_gk_caps_in_team = max_gk_caps.get(team, 0.0)
            if caps == max_gk_caps_in_team and max_gk_caps_in_team >= 0.0:
                starter_prob = 1.0
            else:
                starter_prob = 0.0
        else:
            starter_prob = min(base_prob * intl_factor, 0.2)
            
        # Find the fixture
        match_row = df_match_preds[(df_match_preds['home_team'] == team) | (df_match_preds['away_team'] == team)]
        if len(match_row) == 0:
            continue
        m = match_row.iloc[0]
        is_home = m['home_team'] == team
        
        exp_goals_for = m['expected_goals_home'] if is_home else m['expected_goals_away']
        exp_goals_against = m['expected_goals_away'] if is_home else m['expected_goals_home']
        
        # Minutes
        exp_min_points = 2.0 * starter_prob
        
        # Form adjustment on expected goals and assists per 90 (in-tournament form signal)
        form_xg_boost = 1.0 + 0.25 * wc_goals_count
        form_xa_boost = 1.0 + 0.15 * wc_goals_count
        
        raw_xg90 = row['rec_npxG90']
        raw_xa90 = row['rec_xA90']
        
        # League strength discount factor (based on Opta Power Rankings: Big 5: 85.1, MLS: 73.2, SPL: 68.5)
        league_discount = 1.0
        player_league = str(row.get('league', '')).lower()
        if 'mls' in player_league:
            league_discount = 0.60
        elif 'saudi' in player_league or 'pro_league' in player_league:
            league_discount = 0.50
            
        raw_xg90 = raw_xg90 * league_discount
        raw_xa90 = raw_xa90 * league_discount
        
        # Stabilize low club minutes to prevent small-sample inflation
        if row['time'] < 450 and row['time'] > 0:
            scale = row['time'] / 450.0
            raw_xg90 = raw_xg90 * scale
            raw_xa90 = raw_xa90 * scale
            
        boosted_npxG90 = raw_xg90 * form_xg_boost
        boosted_xA90 = raw_xa90 * form_xa_boost
        
        # Goals
        eg = boosted_npxG90 * (exp_goals_for / 1.3)
        if pos == 'Forward':
            exp_goal_points = (eg * 4.0 + eg * 0.10 * 1.0) * starter_prob
        elif pos == 'Midfielder':
            exp_goal_points = (eg * 5.0 + eg * 0.25 * 1.0) * starter_prob
        elif pos == 'Defender':
            exp_goal_points = (eg * 6.0 + eg * 0.10 * 1.0) * starter_prob
        else:
            exp_goal_points = (eg * 6.0) * starter_prob
            
        # Assists
        ea = boosted_xA90 * (exp_goals_for / 1.3)
        exp_assist_points = (ea * 3.0) * starter_prob
        
        # Clean sheet
        cs_prob = np.exp(-exp_goals_against)
        if pos in ['Goalkeeper', 'Defender']:
            exp_cs_points = (cs_prob * 5.0) * starter_prob
        elif pos == 'Midfielder':
            exp_cs_points = (cs_prob * 1.0) * starter_prob
        else:
            exp_cs_points = 0.0
            
        # Conceded penalty
        if pos in ['Goalkeeper', 'Defender']:
            exp_gc_points = -(exp_goals_against - 1.0 + np.exp(-exp_goals_against)) * starter_prob
        else:
            exp_gc_points = 0.0
            
        # Tackles & chances
        if pos == 'Midfielder':
            tackles_per_90 = 1.0 if (boosted_npxG90 + boosted_xA90) >= 0.3 else 2.0
            exp_tackle_points = (tackles_per_90 * (exp_goals_against / 1.3) * 0.33) * starter_prob
        else:
            exp_tackle_points = 0.0
            
        exp_chance_points = (boosted_xA90 * 1.5 * (exp_goals_for / 1.3) * 0.5) * starter_prob
        exp_sot_points = (boosted_npxG90 * 4.0 * (exp_goals_for / 1.3) * 0.33) * starter_prob
        
        # Qualification booster (removed as requested)
        exp_qual_points = 0.0
        
        exp_points = (exp_min_points + exp_goal_points + exp_assist_points + 
                      exp_cs_points + exp_gc_points + exp_tackle_points + 
                      exp_chance_points + exp_sot_points + exp_qual_points)
                      
        player_exp_points.append({
            'player_name': row['player_name_us'],
            'team_title': team,
            'pos': pos,
            'price': row['price'],
            'points': exp_points,
            'goals': eg,
            'assists': ea,
            'time': starts
        })
    return pd.DataFrame(player_exp_points), df_match_preds

# 2. RUN SOLVER FOR API ENDPOINT
def run_solver_for_api(league, formation, budget):
    print(f"\n[SOLVER] Optimizing squad: league={league}, formation={formation}, budget={budget}")
    
    # 1. Load data source
    is_wc = False
    if league == 'world_cup':
        df, df_match_preds = calculate_wc_expected_points()
        is_wc = True
    elif league == 'home':
        # Global optimal: Load all players from all 5 divisions and combine
        lps = pd.read_csv(os.path.join(workspace_dir, "league_player_stats.csv"))
        df = lps[lps['season'] == 2025].copy()
        # Hard-filter candidate pool (remove benchwarmers/inactive assets)
        df = df[df['time'] >= 450].copy()
        df['pos'] = df['position'].apply(get_position)
        # Calculate price & points
        prices = []
        points = []
        base_prices = {'Goalkeeper': 4.5, 'Defender': 4.5, 'Midfielder': 5.0, 'Forward': 5.0}
        for idx, row in df.iterrows():
            pos = row['pos']
            mins = row['time']
            npxG90 = row['npxG'] / mins * 90.0 if mins > 0 else 0.0
            xA90 = row['xA'] / mins * 90.0 if mins > 0 else 0.0
            stat_score = npxG90 + xA90
            
            base = base_prices[pos]
            premium = min(5.0 * stat_score, 4.5)
            fake_caps = min(row['goals'] * 3 + row['assists'] * 4, 80)
            fame = min(0.02 * fake_caps, 1.5)
            price = round(base + premium + fame, 1)
            prices.append(price)
            
            starts_pct = min(row['games'] / 38.0, 1.0)
            base_pts = (row['goals'] * 4.5 + row['assists'] * 3.0 + (row['time'] / 90.0) * 1.5)
            exp_pts = round(base_pts * starts_pct * 1.2, 2)
            points.append(exp_pts)
        df['price'] = prices
        df['points'] = points
    else:
        # Load league players
        leagues_map = {
            'epl': 'EPL',
            'la_liga': 'La_Liga',
            'serie_a': 'Serie_A',
            'bundesliga': 'Bundesliga',
            'ligue_1': 'Ligue_1'
        }
        db_league_name = leagues_map.get(league, 'EPL')
        lps = pd.read_csv(os.path.join(workspace_dir, "league_player_stats.csv"))
        df = lps[(lps['season'] == 2025) & (lps['league'] == db_league_name)].copy()
        # Hard-filter candidate pool (remove benchwarmers/inactive assets)
        df = df[df['time'] >= 450].copy()
        df['pos'] = df['position'].apply(get_position)
        # Calculate price & points
        prices = []
        points = []
        base_prices = {'Goalkeeper': 4.5, 'Defender': 4.5, 'Midfielder': 5.0, 'Forward': 5.0}
        for idx, row in df.iterrows():
            pos = row['pos']
            mins = row['time']
            npxG90 = row['npxG'] / mins * 90.0 if mins > 0 else 0.0
            xA90 = row['xA'] / mins * 90.0 if mins > 0 else 0.0
            stat_score = npxG90 + xA90
            
            base = base_prices[pos]
            premium = min(5.0 * stat_score, 4.5)
            fake_caps = min(row['goals'] * 3 + row['assists'] * 4, 80)
            fame = min(0.02 * fake_caps, 1.5)
            price = round(base + premium + fame, 1)
            prices.append(price)
            
            starts_pct = min(row['games'] / 38.0, 1.0)
            base_pts = (row['goals'] * 4.5 + row['assists'] * 3.0 + (row['time'] / 90.0) * 1.5)
            exp_pts = round(base_pts * starts_pct * 1.2, 2)
            points.append(exp_pts)
        df['price'] = prices
        df['points'] = points

    print(f"[SOLVER] Total players available in pool for {league}: {len(df)}")
    
    # 2. Parse formation
    if league == 'world_cup':
        req_starters = {
            'Goalkeeper': 1,
            'Defender': 4,
            'Midfielder': 4,
            'Forward': 2
        }
    else:
        parts = [int(x) for x in formation.split('-')]
        req_starters = {
            'Goalkeeper': 1,
            'Defender': parts[0],
            'Midfielder': parts[1],
            'Forward': parts[2]
        }
    
    req_squad = {
        'Goalkeeper': 2,
        'Defender': 5,
        'Midfielder': 5,
        'Forward': 3
    }
    
    current_budget = budget
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        n_players = len(df)
        prob = pulp.LpProblem("Roster_Optimization", pulp.LpMaximize)
        
        # Decision variables
        x_vars = [pulp.LpVariable(f"squad_{i}", cat=pulp.LpBinary) for i in range(n_players)] # 15-player squad
        s_vars = [pulp.LpVariable(f"start_{i}", cat=pulp.LpBinary) for i in range(n_players)] # 11-player starters
        
        # Objective: Maximize expected points of the starting XI, with a small tie-breaker for bench strength
        prob += pulp.lpSum([df.iloc[i]['points'] * s_vars[i] for i in range(n_players)]) + pulp.lpSum([0.001 * df.iloc[i]['points'] * x_vars[i] for i in range(n_players)])
        
        # Constraints
        # Starters <= Squad selection
        for i in range(n_players):
            prob += s_vars[i] <= x_vars[i]
            
        # Total squad size and budget
        prob += pulp.lpSum(x_vars) == 15
        prob += pulp.lpSum([df.iloc[i]['price'] * x_vars[i] for i in range(n_players)]) <= current_budget
        
        # Total starters size
        prob += pulp.lpSum(s_vars) == 11
        
        # Squad positional constraints
        positions = df['pos'].values
        for pos, count in req_squad.items():
            prob += pulp.lpSum([x_vars[i] for i in range(n_players) if positions[i] == pos]) == count
            
        # Starters positional constraints matching the formation
        for pos, count in req_starters.items():
            prob += pulp.lpSum([s_vars[i] for i in range(n_players) if positions[i] == pos]) == count
            
        # Max players per team / nation (limit increases to 4 in knockouts)
        team_limit = 4 if is_wc else 3
        teams = df['team_title'].values
        for team in np.unique(teams):
            prob += pulp.lpSum([x_vars[i] for i in range(n_players) if teams[i] == team]) <= team_limit
            
        # Anti-Stacking Defensive Clashing Filter (for World Cup / domestic matches)
        if is_wc:
            for idx, row_match in df_match_preds.iterrows():
                h, a = row_match['home_team'], row_match['away_team']
                xga_h = row_match['expected_goals_away'] # goals conceded by home
                xga_a = row_match['expected_goals_home'] # goals conceded by away
                
                # If either team in the fixture is expected to concede > 1.0 goals (volatile fixture), cap defensive assets for BOTH teams to <= 1
                if xga_h > 1.0 or xga_a > 1.0:
                    prob += pulp.lpSum([x_vars[i] for i in range(n_players) if teams[i] == h and positions[i] in ['Goalkeeper', 'Defender']]) <= 1
                    prob += pulp.lpSum([x_vars[i] for i in range(n_players) if teams[i] == a and positions[i] in ['Goalkeeper', 'Defender']]) <= 1
                    
        # Enforce Hard Component Bench Floor Constraint
        # For every player i on the bench (b_i = x_vars[i] - s_vars[i] = 1), their expected points must be >= bench_each_floor
        # And the sum of expected points for all 4 bench players must be >= bench_sum_floor
        bench_sum_floor = 20.0 if is_wc else 120.0
        bench_each_floor = 4.5 if is_wc else 30.0
        
        prob += pulp.lpSum([df.iloc[i]['points'] * (x_vars[i] - s_vars[i]) for i in range(n_players)]) >= bench_sum_floor
        
        for i in range(n_players):
            prob += df.iloc[i]['points'] * (x_vars[i] - s_vars[i]) >= bench_each_floor * (x_vars[i] - s_vars[i])
            
        # Print target players details right before solving
        print("\n--- TARGET PLAYERS BEFORE SOLVE ---")
        targets_to_print = ["Mbappe", "Bellingham", "Vinicius", "Kane", "Lukaku", "Merino"]
        
        bellingham_pts = None
        merino_pts = None
        
        for idx_p, row_p in df.iterrows():
            name_p = row_p['player_name']
            if any(t.lower() in name_p.lower() for t in targets_to_print):
                club_p = row_p.get('team_title', 'N/A')
                print(f"  Name: {name_p} | Expected Points: {row_p['points']} | Club: {club_p} | Cost: {row_p['price']}")
                if 'bellingham' in name_p.lower():
                    bellingham_pts = row_p['points']
                elif 'merino' in name_p.lower():
                    merino_pts = row_p['points']
        print("-----------------------------------\n")
        
        # In World Cup mode, execute pre-solve integrity check (disabled under corrected model)
        if is_wc and bellingham_pts is not None and merino_pts is not None:
            pass

        try:
            # Solver with strict 3 seconds limit
            status = prob.solve(pulp.PULP_CBC_CMD(timeLimit=3, msg=False))
            if pulp.LpStatus[status] == "Optimal":
                # Separate starting XI and bench
                starting_idx = [i for i in range(n_players) if s_vars[i].varValue > 0.5]
                squad_idx = [i for i in range(n_players) if x_vars[i].varValue > 0.5]
                bench_idx = [i for i in squad_idx if i not in starting_idx]
                
                print(f"[SOLVER] Optimal squad resolved successfully at budget {current_budget:.1f}")
                return df.iloc[starting_idx].copy(), df.iloc[bench_idx].copy(), current_budget
        except Exception as e:
            print(f"[SOLVER] Solver error on attempt {attempt+1}: {e}")
            
        # Relax budget parameter by 2%
        print(f"[SOLVER] Attempt {attempt+1} infeasible. Relaxing budget by 2% to {current_budget*1.02:.1f}")
        current_budget *= 1.02
        attempt += 1
        
    # Fallback if solver fails or is infeasible
    print("[SOLVER] Solver failed or was infeasible after max attempts. Triggering fallback list.")
    # Pick top players by points in each position
    starting_rows = []
    bench_rows = []
    for pos, sq_count in req_squad.items():
        st_count = req_starters[pos]
        pos_df = df[df['pos'] == pos].sort_values(by='points', ascending=False)
        starting_rows.append(pos_df.head(st_count))
        bench_rows.append(pos_df.iloc[st_count:sq_count])
        
    return pd.concat(starting_rows), pd.concat(bench_rows), current_budget

# 3. HTTP SERVER REQUEST HANDLER
class PredictiveMatrixHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        if parsed_path.path == '/api/optimize':
            params = urlparse.parse_qs(parsed_path.query)
            league = params.get('league', ['epl'])[0]
            formation = params.get('formation', ['4-3-3'])[0]
            budget = float(params.get('budget', [80.0])[0])
            
            try:
                starting_df, bench_df, final_budget = run_solver_for_api(league, formation, budget)
                
                def format_players(df):
                    players = []
                    for idx, row in df.iterrows():
                        if league == 'world_cup':
                            goals_str = f"{row['goals']:.2f} xG" if 'goals' in row else "0.0 xG"
                            assists_str = f"{row['assists']:.2f} xA" if 'assists' in row else "0.0 xA"
                            minutes_str = f"{row['time']}" if 'time' in row else "0"
                        else:
                            goals_str = int(row['goals']) if 'goals' in row else 0
                            assists_str = int(row['assists']) if 'assists' in row else 0
                            minutes_str = int(row['time']) if 'time' in row else 0
                            
                        players.append({
                            'name': row['player_name'],
                            'team': row['team_title'],
                            'position': row['pos'],
                            'cost': f"£{row['price']:.1f}m",
                            'points': f"{row['points']:.1f} PTS",
                            'goals': goals_str,
                            'assists': assists_str,
                            'minutes': minutes_str
                        })
                    return players
                    
                response_data = {
                    'starting_xi': format_players(starting_df),
                    'bench': format_players(bench_df),
                    'budgetUsed': f"£{(starting_df['price'].sum() + bench_df['price'].sum()):.1f}m / £{final_budget:.1f}m",
                    'expectedPoints': f"{starting_df['points'].sum():.1f} PTS"
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            super().do_GET()

def run(server_class=HTTPServer, handler_class=PredictiveMatrixHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == '__main__':
    run()
