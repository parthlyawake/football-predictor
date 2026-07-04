import os
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"

def fetch_bootstrap_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    print(f"Fetching bootstrap data from {url}...")
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data

def fetch_player_history(player_id):
    url = f"https://fantasy.premierleague.com/api/element-summary/{player_id}/"
    r = requests.get(url)
    r.raise_for_status()
    history = r.json().get('history', [])
    for entry in history:
        entry['player_id'] = player_id
    return history

def main():
    # 1. Fetch bootstrap data
    bootstrap = fetch_bootstrap_data()
    elements = bootstrap['elements']
    teams = {t['code']: t['name'] for t in bootstrap['teams']}
    team_names_by_id = {t['id']: t['name'] for t in bootstrap['teams']}
    
    positions = {
        1: 'Goalkeeper',
        2: 'Defender',
        3: 'Midfielder',
        4: 'Forward'
    }
    
    # Map team_name and position to players_master
    df_players = pd.DataFrame(elements)
    df_players['team_name'] = df_players['team'].map(team_names_by_id)
    df_players['position'] = df_players['element_type'].map(positions)
    
    players_master_path = os.path.join(workspace_dir, "players_master.csv")
    df_players.to_csv(players_master_path, index=False)
    print(f"Saved {len(df_players)} players to {players_master_path}")
    
    # 2. Fetch histories concurrently
    player_ids = df_players['id'].tolist()
    all_histories = []
    
    print(f"Fetching gameweek histories for {len(player_ids)} players concurrently...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_player_history, p_id): p_id for p_id in player_ids}
        for future in as_completed(futures):
            p_id = futures[future]
            try:
                history = future.result()
                all_histories.extend(history)
            except Exception as e:
                print(f"Error fetching history for player {p_id}: {e}")
                
    df_history = pd.DataFrame(all_histories)
    # Reorder columns to ensure player_id is at the end or wherever, and match the original
    if not df_history.empty:
        # Move player_id to the end or match the columns check
        cols = [c for c in df_history.columns if c != 'player_id'] + ['player_id']
        df_history = df_history[cols]
        
    history_path = os.path.join(workspace_dir, "player_gameweek_history.csv")
    df_history.to_csv(history_path, index=False)
    print(f"Saved {len(df_history)} gameweek history rows to {history_path}")

if __name__ == "__main__":
    main()
