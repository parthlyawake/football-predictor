# Walkthrough - Fantasy Football Predictor (Round of 16 Calibration V7)

> [!IMPORTANT]
> **Booster Removal & Rankings Verification**: We have dropped the `+2 EV × advance-probability` qualification booster entirely. We also audited the position rankings and verified that **Johan Manzambi** now starts on merit above Enzo Fernández and Kevin De Bruyne, and **Erling Haaland** and **Harry Kane** are correctly active in the pool with their correct starting status and knockout fixtures.

---

## 1. Opponent & Fixture Verification (Kane & Haaland)
We verified that both **Harry Kane** (England) and **Erling Haaland** (Norway) are active in the pool, and their confirmed Round of 16 fixtures are present and active in the database:
1.  **England**: Plays **Mexico** on July 6, 2026. This match is active in the results matrix with expected goals of **1.33 (England)** and **1.25 (Mexico)**.
    *   **Harry Kane** has **13.51 expected points** (ranked #3 Forward). He is not picked in the squad because Lionel Messi (21.00 PTS) and Kylian Mbappé (16.38 PTS) have higher expected points, and Matheus Cunha (8.63 PTS, £9.0m) is preferred as a cheaper bench option.
2.  **Norway**: Plays **Brazil** on July 5, 2026. This match is active in the results matrix with expected goals of **2.04 (Brazil)** and **0.79 (Norway)**.
    *   **Erling Haaland** has **8.16 expected points** (ranked #5 Forward). His expected points are lower than Kane's because Norway faces a very difficult fixture against Brazil (expected goals for Norway is scaled to a low 0.79). Since he costs £10.5m, he is outranked on merit and budget efficiency by Matheus Cunha (£9.0m, 8.63 PTS).

---

## 2. Enzo Fernández & Kevin De Bruyne vs. Johan Manzambi
*   **The Discrepancy**: Enzo Fernández and Kevin De Bruyne were previously ranking above Johan Manzambi despite Manzambi having a much better real tournament (3 goals).
*   **The Cause**: The `+2 EV` qualification booster was heavily inflating Enzo's (+1.81 PTS) and De Bruyne's (+1.47 PTS) expected points because their respective national teams (Argentina and Belgium) were heavy favorites to advance, whereas Switzerland (Manzambi's team) was a slight underdog (+1.18 PTS booster).
*   **The Fix**: Dropping the qualification booster completely removes this distortion.
*   **Current Standings (Without Qualification Booster)**:
    *   **Johan Manzambi**: **7.23 expected points** (starts = 27, raw_npxG = 0.306, raw_xA = 0.233, tournament goals = 3).
    *   **Enzo Fernández**: **6.70 expected points** (starts = 36, raw_npxG = 0.175, raw_xA = 0.234, tournament goals = 0).
    *   **Kevin De Bruyne**: **6.15 expected points** (starts = 18, raw_npxG = 0.071, raw_xA = 0.485, tournament goals = 1).
*   **Verdict**: Manzambi now ranks **above** both Enzo Fernández and Kevin De Bruyne on merit. Enzo Fernández is completely dropped from the squad, while De Bruyne sits on the bench as the backup midfielder.

---

## 3. Position Rankings: Top 15 Candidates

### Goalkeepers
1.  **Emiliano Martínez** (Argentina) — **4.97 PTS** | Price: £5.5m (starts=26.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Egypt)
2.  **Mike Maignan** (France) — **4.21 PTS** | Price: £4.6m (starts=37.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Paraguay)
3.  **Alisson** (Brazil) — **4.03 PTS** | Price: £5.5m (starts=26.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Norway)
4.  **Thibaut Courtois** (Belgium) — **3.51 PTS** | Price: £5.5m (starts=32.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs USA)
5.  **Yassine Bounou** (Morocco) — **3.51 PTS** | Price: £5.2m (starts=30.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=1, vs Canada)
6.  **Unai Simón** (Spain) — **3.01 PTS** | Price: £5.5m (starts=37.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Portugal)
7.  **Jordan Pickford** (England) — **3.00 PTS** | Price: £5.5m (starts=38.0, raw_xg90=0.000, raw_xa90=0.027, wc_goals=0, vs Mexico)
8.  **Camilo Vargas** (Colombia) — **2.88 PTS** | Price: £5.2m (starts=34.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=2, vs Switzerland)
9.  **Gregor Kobel** (Switzerland) — **2.75 PTS** | Price: £4.6m (starts=34.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Colombia)
10. **Diogo Costa** (Portugal) — **2.60 PTS** | Price: £5.2m (starts=34.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Spain)
11. **Maxime Crépeau** (Canada) — **2.02 PTS** | Price: £4.8m (starts=34.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs Morocco)
12. **Gatito Fernández** (Paraguay) — **1.01 PTS** | Price: £4.8m (starts=34.0, raw_xg90=0.000, raw_xa90=0.000, wc_goals=0, vs France)
13. **Dean Henderson** (England) — **0.00 PTS** | Price: £3.8m
14. **José Sá** (Portugal) — **0.00 PTS** | Price: £3.8m
15. **David Raya** (Spain) — **0.00 PTS** | Price: £3.8m

### Defenders
1.  **Nahuel Molina** (Argentina) — **8.23 PTS** | Price: £5.2m (starts=26.0, raw_xg90=0.056, raw_xa90=0.390, wc_goals=0, vs Egypt)
2.  **Maxim De Cuyper** (Belgium) — **8.18 PTS** | Price: £6.5m (starts=30.0, raw_xg90=0.070, raw_xa90=0.671, wc_goals=1, vs USA)
3.  **Jules Koundé** (France) — **7.62 PTS** | Price: £6.5m (starts=30.0, raw_xg90=0.086, raw_xa90=0.328, wc_goals=0, vs Paraguay)
4.  **Nuno Mendes** (Portugal) — **6.57 PTS** | Price: £5.2m (starts=20.0, raw_xg90=0.215, raw_xa90=0.538, wc_goals=1, vs Spain)
5.  **Achraf Hakimi** (Morocco) — **6.51 PTS** | Price: £5.2m (starts=18.0, raw_xg90=0.187, raw_xa90=0.127, wc_goals=1, vs Canada)
6.  **William Saliba** (France) — **5.84 PTS** | Price: £6.5m (starts=31.0, raw_xg90=0.047, raw_xa90=0.107, wc_goals=1, vs Paraguay)
7.  **Lisandro Martínez** (Argentina) — **4.78 PTS** | Price: £5.2m (starts=18.0, raw_xg90=0.011, raw_xa90=0.005, wc_goals=1, vs Egypt)
8.  **Johan Mojica** (Colombia) — **4.47 PTS** | Price: £6.5m (starts=35.0, raw_xg90=0.045, raw_xa90=0.180, wc_goals=3, vs Switzerland)
9.  **Pedro Porro** (Spain) — **4.30 PTS** | Price: £6.5m (starts=34.0, raw_xg90=0.078, raw_xa90=0.167, wc_goals=0, vs Portugal)
10. **Marquinhos** (Brazil) — **4.11 PTS** | Price: £5.2m (starts=14.0, raw_xg90=0.007, raw_xa90=0.000, wc_goals=0, vs Norway)
11. **Marc Cucurella** (Spain) — **3.83 PTS** | Price: £6.5m (starts=34.0, raw_xg90=0.045, raw_xa90=0.116, wc_goals=0, vs Portugal)
12. **Aymeric Laporte** (Spain) — **3.57 PTS** | Price: £5.2m (starts=25.0, raw_xg90=0.069, raw_xa90=0.002, wc_goals=0, vs Portugal)
13. **Pau Cubarsí** (Spain) — **3.05 PTS** | Price: £6.5m (starts=31.0, raw_xg90=0.001, raw_xa90=0.008, wc_goals=0, vs Portugal)
14. **John Stones** (England) — **2.96 PTS** | Price: £4.3m (starts=9.0, raw_xg90=0.000, raw_xa90=0.015, wc_goals=1, vs Mexico)
15. **Cristian Romero** (Argentina) — **1.32 PTS** | Price: £5.2m (starts=23.0, raw_xg90=0.079, raw_xa90=0.123, wc_goals=0, vs Egypt)

### Midfielders
1.  **Ousmane Dembélé** (France) — **17.87 PTS** | Price: £6.5m (starts=22.0, raw_xg90=0.452, raw_xa90=0.402, wc_goals=4, vs Paraguay)
2.  **Michael Olise** (France) — **12.78 PTS** | Price: £8.0m (starts=32.0, raw_xg90=0.437, raw_xa90=0.456, wc_goals=1, vs Paraguay)
3.  **Vinícius Júnior** (Brazil) — **12.01 PTS** | Price: £10.0m (starts=36.0, raw_xg90=0.329, raw_xa90=0.273, wc_goals=4, vs Norway)
4.  **Lamine Yamal** (Spain) — **9.62 PTS** | Price: £8.5m (starts=28.0, raw_xg90=0.593, raw_xa90=0.391, wc_goals=1, vs Portugal)
5.  **Johan Manzambi** (Switzerland) — **7.23 PTS** | Price: £8.0m (starts=27.0, raw_xg90=0.306, raw_xa90=0.233, wc_goals=3, vs Colombia)
6.  **Enzo Fernández** (Argentina) — **6.70 PTS** | Price: £8.0m (starts=36.0, raw_xg90=0.175, raw_xa90=0.234, wc_goals=0, vs Egypt)
7.  **Kevin De Bruyne** (Belgium) — **6.15 PTS** | Price: £6.5m (starts=18.0, raw_xg90=0.071, raw_xa90=0.485, wc_goals=1, vs USA)
8.  **Casemiro** (Brazil) — **6.13 PTS** | Price: £8.0m (starts=34.0, raw_xg90=0.221, raw_xa90=0.092, wc_goals=1, vs Norway)
9.  **Alexis Mac Allister** (Argentina) — **5.92 PTS** | Price: £8.0m (starts=37.0, raw_xg90=0.120, raw_xa90=0.150, wc_goals=1, vs Egypt)
10. **Bruno Fernandes** (Portugal) — **5.92 PTS** | Price: £8.0m (starts=35.0, raw_xg90=0.152, raw_xa90=0.695, wc_goals=0, vs Spain)
11. **Jude Bellingham** (England) — **4.67 PTS** | Price: £9.5m (starts=28.0, raw_xg90=0.181, raw_xa90=0.050, wc_goals=2, vs Mexico)
12. **Youri Tielemans** (Belgium) — **3.84 PTS** | Price: £8.0m (starts=25.0, raw_xg90=0.040, raw_xa90=0.070, wc_goals=2, vs USA)
13. **Granit Xhaka** (Switzerland) — **3.53 PTS** | Price: £8.0m (starts=34.0, raw_xg90=0.032, raw_xa90=0.082, wc_goals=1, vs Colombia)
14. **Valentín Barco** (Argentina) — **1.62 PTS** | Price: £8.0m (starts=27.0, raw_xg90=0.343, raw_xa90=0.127, wc_goals=0, vs Egypt)
15. **Bilal El Khannouss** (Morocco) — **1.38 PTS** | Price: £8.0m (starts=25.0, raw_xg90=0.315, raw_xa90=0.320, wc_goals=0, vs Canada)

### Forwards
1.  **Lionel Messi** (Argentina) — **21.00 PTS** | Price: £11.0m (starts=24.0, raw_xg90=0.500, raw_xa90=0.400, wc_goals=6, vs Egypt)
2.  **Kylian Mbappé** (France) — **16.38 PTS** | Price: £10.5m (starts=31.0, raw_xg90=0.668, raw_xa90=0.109, wc_goals=4, vs Paraguay)
3.  **Harry Kane** (England) — **13.51 PTS** | Price: £10.5m (starts=31.0, raw_xg90=0.783, raw_xa90=0.262, wc_goals=5, vs Mexico)
4.  **Matheus Cunha** (Brazil) — **8.63 PTS** | Price: £9.0m (starts=33.0, raw_xg90=0.318, raw_xa90=0.222, wc_goals=3, vs Norway)
5.  **Erling Haaland** (Norway) — **8.16 PTS** | Price: £10.5m (starts=35.0, raw_xg90=0.856, raw_xa90=0.145, wc_goals=4, vs Brazil)
6.  **Bradley Barcola** (France) — **8.13 PTS** | Price: £9.0m (starts=29.0, raw_xg90=0.390, raw_xa90=0.169, wc_goals=1, vs Paraguay)
7.  **Luis Díaz** (Colombia) — **7.06 PTS** | Price: £9.0m (starts=32.0, raw_xg90=0.439, raw_xa90=0.467, wc_goals=1, vs Switzerland)
8.  **Julián Álvarez** (Argentina) — **5.15 PTS** | Price: £9.0m (starts=29.0, raw_xg90=0.359, raw_xa90=0.264, wc_goals=2, vs Egypt)
9.  **Cristiano Ronaldo** (Portugal) — **5.13 PTS** | Price: £9.0m (starts=30.0, raw_xg90=0.398, raw_xa90=0.035, wc_goals=2, vs Spain)
10. **Brahim Diaz** (Morocco) — **5.08 PTS** | Price: £9.0m (starts=30.0, raw_xg90=0.198, raw_xa90=0.233, wc_goals=1, vs Canada)
11. **Mikel Oyarzabal** (Spain) — **4.16 PTS** | Price: £9.0m (starts=34.0, raw_xg90=0.168, raw_xa90=0.134, wc_goals=2, vs Portugal)
12. **Jean-Philippe Mateta** (France) — **1.94 PTS** | Price: £9.0m (starts=32.0, raw_xg90=0.752, raw_xa90=0.039, wc_goals=0, vs Paraguay)
13. **Ollie Watkins** (England) — **1.69 PTS** | Price: £9.0m (starts=37.0, raw_xg90=1.069, raw_xa90=0.140, wc_goals=0, vs Mexico)
14. **Endrick** (Brazil) — **1.47 PTS** | Price: £7.5m (starts=1.0, raw_xg90=0.414, raw_xa90=0.309, wc_goals=0, vs Norway)
15. **Giuliano Simeone** (Argentina) — **1.23 PTS** | Price: £9.0m (starts=31.0, raw_xg90=0.214, raw_xa90=0.254, wc_goals=0, vs Egypt)
