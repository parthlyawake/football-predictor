# Fantasy Football Predictor & Optimizer

This project provides a data-driven prediction and optimization pipeline for two distinct tracks of fantasy football:
1.  **Track A (Domestic League)**: Machine-learning-based gameweek predictions and squad optimization for Europe's top-5 domestic leagues (specifically backtested and validated on the English Premier League 2025/26 season).
2.  **Track B (World Cup 2026)**: Dynamic squad optimization for the FIFA World Cup 2026 knockout stages (specifically the Round of 16), featuring Poisson goal/assist probability modelling, ELO ratings, in-tournament form-blending, and tournament rule constraints (e.g. 2-5-5-3 squad formation footprint and team limits).

---

## Codebase Pipeline Structure

The core codebase is organized inside the `src/` directory, reflecting a clean data science and optimization pipeline:

```
src/
├── fetch_fpl_data.py          # Fetches live FPL players and gameweek history from the official FPL API
├── clean_data.py              # Sanitizes and compiles club and international datasets
├── feature_engineering.py     # Generates rolling averages, forms, and fixtures difficulty features
├── train_predict.py           # Trains Ridge/RandomForest models on player features to predict expected points
├── optimizer.py               # Solves the MILP (Mixed-Integer Linear Programming) squad constraints using PuLP
├── parse_squads.py            # Extracts verified rosters from the official FIFA Squad Lists PDF
├── update_knockouts.py        # Appends knockout fixtures and dates to the results dataset
├── refresh_results.py         # Pulls latest results and updates stats dynamically
└── run_pipeline.py            # Coordinates the end-to-end execution of the predictive pipeline
```

*Note: All debugging and diagnostic scripts have been moved to the `scratch/` directory and are ignored by git.*

---

## Data Management & Sourcing

To maintain a clean and lightweight repository while avoiding GitHub's large file limit warnings, data files are sorted into three distinct buckets:

### Bucket A: Publicly Downloadable (Not Distributed)
These files are excluded from version control (`.gitignore`) and must be downloaded or fetched before running the pipeline:
1.  **Kaggle International Football Dataset** (`results.csv`, `goalscorers.csv`, `shootouts.csv`, `former_names.csv`):
    *   **Source**: [Kaggle International Football Results (1872-2024)](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017)
    *   **Instructions**: Download the CSV files and place them in the root directory.
2.  **FIFA World Cup 2026 Squad Lists PDF** (`SquadLists-English.pdf`):
    *   **Source**: [FIFA Official Document Portal](https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf)
    *   **Instructions**: Download the PDF, place it in the root directory, and run `python src/parse_squads.py` to compile `data/world_cup_squads.csv`.
3.  **FPL Live API Data** (`players_master.csv`, `player_gameweek_history.csv`):
    *   **Source**: Official Fantasy Premier League API (`https://fantasy.premierleague.com/api/bootstrap-static/` and `https://fantasy.premierleague.com/api/element-summary/{player_id}/`)
    *   **Instructions**: Run `python src/fetch_fpl_data.py` to pull fresh data from the API and generate these files.

### Bucket B: Committed Locally (Small Files)
These files are committed directly to the repository as they are small enough (under a few megabytes) and have no clean public download link:
*   `league_player_stats.csv` (1.30 MB): Seasonal club player metrics.
*   `data/*.parquet`: Feature and prediction parquets (`features.parquet`, `predictions.parquet`, `intl_team_match.parquet`, `intl_goalscorers.parquet`, `intl_shootouts.parquet`, `club_player_gameweek.parquet`).
*   `data/players_master_wc.csv` & `players_master_wc_v2.csv` (0.08 MB): Mapped player masters for the World Cup track.
*   `data/world_cup_squads.csv` (0.10 MB): Extracted World Cup rosters.
*   `data/optimized_squad_gw30.csv` & `optimized_wc_squad.csv`: Resolved output files.

### Bucket C: Git LFS (Large Files)
*   `player_match_data.csv` (23.25 MB): Contains granular player match history.
*   **Prerequisite**: You must have **Git LFS (Large File Storage)** installed to clone this file correctly.
    *   Run `git lfs install` before cloning.
    *   If already cloned without Git LFS, run `git lfs pull` to replace the text pointer files with the real CSV data.

---

## How to Run the Pipeline

### Prerequisites
Install the required dependencies:
```bash
pip install pandas numpy scikit-learn pulp requests pypdf
```

### End-to-End Execution
1.  **Sourcing Data**: Place the Kaggle datasets and FIFA PDF in the root directory, then run the fetch and parse scripts:
    ```bash
    python src/fetch_fpl_data.py
    python src/parse_squads.py
    ```
2.  **Execute the Predictor and Optimizer**:
    ```bash
    python src/run_pipeline.py
    ```
3.  **Run the Interactive Dashboard / Solver Server**:
    The web optimizer relies on a Flask backend:
    ```bash
    python server.py
    ```
    Then open `index.html` in your browser to interactively build and optimize squads.

---

## Known Limitations & Calibration Notes

*   **Track A Validation**: The validation and backtesting models have been verified strictly against the **English Premier League (EPL)**. While other top-5 European divisions are present in the player stats database, the ML model features and coefficients have not been separately tuned for La Liga, Serie A, Bundesliga, or Ligue 1.
*   **Track B Calibration**: Sourcing international data dynamically introduces challenges due to player name variations between club databases (Understat) and official FIFA rosters. The pipeline matches these using a token-intersection helper. 
*   **Form-Blending & League Strength Discounts**: To prevent Messi (MLS) and Ronaldo (Saudi Pro League) from dominating the solver projections on the strength of season-long club stats from weaker divisions, the model applies an Opta-derived league-strength discount multiplier: **0.60** for MLS and **0.50** for the Saudi Pro League.
*   **Knockout Stages**: The qualification booster has been completely removed to avoid rewarding players from heavy-favorite nations regardless of their individual starting status or current form. All starting probabilities for key players are audited against confirmed lineups.
