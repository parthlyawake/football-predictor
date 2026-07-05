import fitz
import pandas as pd
import numpy as np
import os
import unicodedata
import re

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(workspace_dir, "data")
pdf_path = os.path.join(workspace_dir, "SquadLists-English.pdf")

# Name normalization function (re-used from clean_data.py)
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

# Team mapping dictionary
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

def parse_pdf():
    print("=== Parsing SquadLists-English.pdf ===")
    doc = fitz.open(pdf_path)
    squad_players = []
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        lines = [line.strip() for line in page.get_text().split("\n") if line.strip()]
        
        # Team is lines[0] split by code
        team_raw = lines[0]
        team_name = team_raw.split(" (")[0].strip()
        
        # Find GOALS index
        goals_idx = lines.index("GOALS")
        start_idx = goals_idx + 1
        
        # 26 players, 10 lines per player
        for i in range(26):
            block = lines[start_idx + i*10 : start_idx + (i+1)*10]
            pos = block[0]
            player_name = block[1]
            first_names = block[2]
            last_names = block[3]
            dob = block[5]
            club = block[6]
            caps = int(block[8])
            goals = int(block[9])
            
            squad_players.append({
                'team': team_name,
                'position': pos,
                'player_name': player_name,
                'first_names': first_names,
                'last_names': last_names,
                'dob': dob,
                'club': club,
                'caps': caps,
                'goals': goals
            })
            
    df_squads = pd.DataFrame(squad_players)
    output_path = os.path.join(data_dir, "world_cup_squads.csv")
    df_squads.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Parsed {len(df_squads)} players from {len(doc)} teams. Saved to {output_path}")
    
    # Match against FPL/Understat player pool
    print("\n=== Matching World Cup Squads against FPL/Understat Pool ===")
    pm = pd.read_csv(os.path.join(workspace_dir, "players_master.csv"))
    pm['national_team'] = pm['region'].map(region_to_team)
    
    stop_words = {'de', 'da', 'dos', 'di', 'van', 'der', 'le', 'la', 'von', 'and', 'the', 'of', 'junior', 'jr', 'filho', 'neto', 'i'}
    
    # Dictionary to store FPL player matching to WC squad
    fpl_to_wc = {}
    
    # Loop over FPL players and try to find a match in the WC squad
    matched_count = 0
    for idx, fpl_row in pm.iterrows():
        fpl_id = fpl_row['id']
        fpl_team = fpl_row['national_team']
        
        if not isinstance(fpl_team, str):
            continue  # National team must match, skip players without team
            
        fpl_first = normalize_name(fpl_row['first_name'])
        fpl_second = normalize_name(fpl_row['second_name'])
        fpl_full = normalize_name(fpl_row['first_name'] + " " + fpl_row['second_name'])
        
        # Filter WC squad for this team (if team matches)
        candidates = df_squads[df_squads['team'] == fpl_team]
        if len(candidates) == 0:
            continue
            
        found = None
        # Check strict matches within team
        # 1. Exact full name
        match1 = candidates[candidates['player_name'].apply(normalize_name) == fpl_full]
        if len(match1) == 1:
            found = match1.iloc[0]
        elif len(candidates[(candidates['first_names'].apply(normalize_name) + " " + candidates['last_names'].apply(normalize_name)) == fpl_full]) == 1:
            found = candidates[(candidates['first_names'].apply(normalize_name) + " " + candidates['last_names'].apply(normalize_name)) == fpl_full].iloc[0]
            
        # 2. Strict token matching if not found
        if found is None:
            fpl_first_tokens = set(fpl_first.split()) - stop_words
            fpl_last_tokens = set(fpl_second.split()) - stop_words
            
            fpl_known = normalize_name(fpl_row['known_name'])
            if fpl_known:
                known_list = list(fpl_known.split())
                if len(known_list) > 1:
                    fpl_first_tokens.update(set(known_list[:-1]) - stop_words)
                    fpl_last_tokens.update(set([known_list[-1]]) - stop_words)
                else:
                    fpl_last_tokens.update(set(known_list) - stop_words)
            
            best_cand = None
            best_overlap = 0
            for c_idx, c_row in candidates.iterrows():
                c_first_tokens = set(normalize_name(c_row['first_names']).split()) - stop_words
                c_last_tokens = set(normalize_name(c_row['last_names']).split()) - stop_words
                c_all_tokens = set(normalize_name(c_row['player_name']).split()) - stop_words
                
                # Require both first name and last name to match at least one token (excluding stop words)
                first_match = len(fpl_first_tokens.intersection(c_first_tokens)) >= 1
                last_match = len(fpl_last_tokens.intersection(c_last_tokens)) >= 1
                             
                if first_match and last_match:
                    overlap = len(c_all_tokens.intersection(set(fpl_full.split())))
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_cand = c_row
                        
            if best_cand is not None:
                found = best_cand
                
        if found is not None:
            fpl_to_wc[fpl_id] = {
                'wc_team': found['team'],
                'wc_player_name': found['player_name'],
                'wc_club': found['club']
            }
            matched_count += 1
            
    print(f"Matched FPL/Understat Players: {matched_count} out of {len(pm)} FPL players.")
    
    # Save mapping to players_master for Track B model consumption
    pm['wc_matched_team'] = pm['id'].map(lambda x: fpl_to_wc[x]['wc_team'] if x in fpl_to_wc else None)
    pm['wc_matched_name'] = pm['id'].map(lambda x: fpl_to_wc[x]['wc_player_name'] if x in fpl_to_wc else None)
    
    # Report unmatched WC squad players from active teams in FPL
    # (i.e. players in WC squad whose team has FPL representation, but who themselves aren't in FPL/Understat)
    active_wc_squads = df_squads[df_squads['team'].isin(pm['national_team'].dropna().unique())].copy()
    
    # Which of these active WC players were NOT matched to FPL?
    matched_wc_names = set(fpl_to_wc[x]['wc_player_name'] for x in fpl_to_wc)
    unmatched_wc = active_wc_squads[~active_wc_squads['player_name'].isin(matched_wc_names)].copy()
    
    print(f"Total WC squad players in FPL countries: {len(active_wc_squads)}")
    print(f"Unmatched WC squad players (e.g. non-top-5-league players): {len(unmatched_wc)}")
    
    # Save unmatched WC players to CSV
    unmatched_wc_path = os.path.join(data_dir, "unmatched_wc_players.csv")
    unmatched_wc[['team', 'position', 'player_name', 'club', 'caps', 'goals']].to_csv(unmatched_wc_path, index=False)
    print(f"Saved unmatched WC squad players report to {unmatched_wc_path}")
    
    # Save modified players master with wc eligibility flag
    pm.to_csv(os.path.join(data_dir, "players_master_wc.csv"), index=False)
    print("Saved enriched players master to data/players_master_wc.csv")

if __name__ == "__main__":
    parse_pdf()
