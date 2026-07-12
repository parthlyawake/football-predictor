# Fantasy Football Predictor & Optimizer

A full-stack fantasy football performance predictor and squad optimizer built to assist managers in selecting optimal teams. The system features two main tracks:
1. **Track A (Domestic Leagues)**: Machine learning predictions and Mixed-Integer Linear Programming (MILP) optimization for Europe's top 5 domestic divisions (English Premier League, La Liga, Serie A, Bundesliga, Ligue 1) backtested on the 2025/26 season.
2. **Track B (World Cup 2026)**: Dynamic squad optimization for the FIFA World Cup 2026 knockout stages, utilizing custom Poisson goal/assist models, historical team Elo ratings, in-tournament form blending, and tournament rules constraints.

This project was built collaboratively to bridge machine learning predictions with mathematical optimization and responsive web design.

---

## Features

### 1. Machine Learning & Predictive Modeling
- **Expected Points (xP) Prediction**: Trains Ridge and Random Forest models on historical player match records (using rolling forms, fixture difficulties, and team stats) to project expected points.
- **International Poisson Goals Model**: Calculates expected goals/assists per upcoming fixture for Track B, fitted on international match results using maximum likelihood estimation.
- **Team Elo Ratings**: Tracks international team strengths using chronologically simulated Elo ratings across all historical FIFA matches.
- **League Strength Discounts**: Applies Opta-derived multipliers (e.g. 0.60 for MLS, 0.50 for Saudi Pro League) to normalize stats from non-European leagues.

### 2. Mixed-Integer Linear Programming (MILP) Optimization
- Solves squad selection using the PuLP framework to maximize starting XI expected points + captain bonus points.
- Enforces strict roster constraints:
  - **Roster Footprint**: 15-player squad (2 Goalkeepers, 5 Defenders, 5 Midfielders, 3 Forwards).
  - **Starting XI**: 11 players conforming to valid formations (1 GK, Def >= 3, Mid >= 2, Fwd >= 1).
  - **Team Limit constraints**: Max 3 players per country/club (relaxed to max 5 in the Quarter-Final script).
  - **Budget constraints**: **£100.0m** for domestic leagues, **£105.0m** for the World Cup.

### 3. Official FIFA Integration (Track B)
- Parses roster sheets directly from the official FIFA Squad Lists PDF.
- Merges official fantasy prices and positions from `wc2026_players_prices.csv` using fuzzy name-matching logic: handles diacritics removal, token subset comparisons, and country filtering to resolve names like *Martin Ødegaard* and *Vinícius Júnior* without shared player IDs.

### 4. Standalone Quarter-Final Optimizer
- Includes a dedicated utility `predict_qf_squad.py` that imports data loading functions, filters the player pool to the 8 QF qualified nations, warns if any country has zero matching players, and solves the optimal squad under a relaxed **5-player-per-nation** constraint.

### 5. Premium Interactive Web Dashboard
- **Theme Toggle**: Switch between Light Mode (white cards, `#f1f3f5` background) and Dark Mode (dark cards, `#101114` background) fluidly with zero state loss or page reload.
- **Visual Pitch Representation**: Interactive soccer field displaying player kits colored by club/country (e.g., Argentinian white/blue stripes, French navy) with captain "C" / vice-captain "V" overlays and price change indicators.
- **Stat Cards & Stepper**: 3-card filter row (Budget Limit with select overlay, Budget Used, Projected Points) with lift animations and diagonal light sweep hover effects. Features an interactive round stepper (Round 1 - Final) or domestic gameweek tracker.
- **Live API Binding**: Calls `/api/optimize` dynamically. Automatically falls back to pre-compiled static predictions in `data/dashboard_data.js` if the backend server is offline.

---

## Tech Stack
- **Backend/Data Science**: Python 3.x, PuLP (MILP Solver), pandas, numpy, scikit-learn, rapidfuzz, requests, pypdf
- **Frontend/UI**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (Custom Properties, CSS Keyframes, CSS Transitions)
- **Web Server**: Python `http.server` & `SimpleHTTPRequestHandler`

---

## Project Structure

```
.
├── data/
│   ├── club_player_gameweek.parquet  # Parquet containing domestic player gameweek stats
│   ├── dashboard_data.js             # Static fallback data for the web UI dashboard
│   ├── features.parquet              # Compiled training features
│   ├── intl_team_match.parquet       # Parsed international matches history
│   ├── players_master_wc_v2.csv      # Mapped World Cup master player pool
│   └── world_cup_squads.csv          # Extracted World Cup team rosters
├── src/
│   ├── clean_data.py                 # Sanitizes raw source files into parquet datasets
│   ├── feature_engineering.py        # Computes forms, rolling metrics, and difficulties
│   ├── fetch_fpl_data.py             # Fetches live domestic player info from FPL API
│   ├── generate_dashboard_data.py    # Generates static fallback dashboard_data.js
│   ├── optimizer.py                  # Standard domestic MILP solver implementation
│   ├── parse_squads.py               # Extracts rosters from official FIFA PDF
│   ├── run_pipeline.py               # Main pipeline execution orchestrator
│   └── track_b_model.py              # Main World Cup prediction and optimizer pipeline
├── index.html                        # Redesigned interactive sports-app HTML dashboard
├── server.py                         # HTTP API endpoint handler binding optimizer to UI
├── predict_qf_squad.py               # Standalone Quarter-Final squad solver utility
├── wc2026_players_prices.csv         # Official FIFA World Cup fantasy player prices/positions
└── README.md                         # Project documentation
```

---

## Setup & How to Run

### 1. Install Dependencies
Clone the repository, then install Python requirements:
```bash
pip install pandas numpy scikit-learn pulp requests pypdf rapidfuzz
```

### 2. Sourcing Data (First Run)
Place raw Kaggle datasets (`results.csv`, `goalscorers.csv`, `shootouts.csv`, `former_names.csv`) and the FIFA PDF (`SquadLists-English.pdf`) in the root directory. Run the parsers:
```bash
python src/fetch_fpl_data.py
python src/parse_squads.py
```

### 3. Run Pipeline Predictions
Generate expected points predictions and optimal squads across all divisions:
```bash
python src/run_pipeline.py
```

### 4. Launch the Web Dashboard
Start the HTTP API backend:
```bash
python server.py
```
Visit `http://localhost:8000` in your web browser. 

*Note: Opening `index.html` directly in the browser via file protocol (`file:///...`) works, but will rely on static fallback data instead of sending live API calls to the server.*

### 5. Run Standalone QF Optimizer
Generate the one-off Quarter-Final squad prediction:
```bash
python predict_qf_squad.py
```

---

## Data Sources
- **Track A**: Official FPL API, `league_player_stats.csv`, and `player_match_data.csv`.
- **Track B**: Official FIFA World Cup 2026 Squad Lists, Kaggle International Football Results (1872-present), and official fantasy prices from `wc2026_players_prices.csv`.
