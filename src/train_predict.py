import pandas as pd
import numpy as np
import os
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

workspace_dir = r"c:\Users\Parth\OneDrive\Desktop\football-aku"
data_dir = os.path.join(workspace_dir, "data")

def run_backtest():
    print("=== Phase 2: Model Training and Backtesting ===")
    
    features_path = os.path.join(data_dir, "features.parquet")
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found at {features_path}. Run feature_engineering.py first.")
        
    df = pd.read_parquet(features_path)
    
    # Encode position as categorical / numeric
    pos_map = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}
    df['position_code'] = df['position'].map(pos_map).fillna(0).astype(int)
    
    # Define features
    feature_cols = [
        'xG90_3', 'xA90_3', 'npxG90_3',
        'xG90_5', 'xA90_5', 'npxG90_5',
        'xG90_10', 'xA90_10', 'npxG90_10',
        'fpl_roll_min_3', 'fpl_roll_min_5',
        'rotation_risk',
        'opp_goals_conceded_5', 'opp_xG_conceded_5',
        'opp_goals_conceded_10', 'opp_xG_conceded_10',
        'was_home',
        'corners_and_indirect_freekicks_order', 'direct_freekicks_order', 'penalties_order',
        'value', 'selected',
        'position_code'
    ]
    
    target_col = 'target_points'
    
    # Dynamic round range detection
    rounds = sorted(list(df['round'].unique()))
    print(f"Detected {len(rounds)} gameweeks: {rounds}")
    
    # Backtest starts at round 10 to ensure we have enough training data
    start_round = 10
    backtest_rounds = [r for r in rounds if r >= start_round]
    print(f"Backtesting over rounds {backtest_rounds[0]} to {backtest_rounds[-1]} (predicting rounds {backtest_rounds[0]+1} to {backtest_rounds[-1]+1}).")
    
    predictions = []
    actuals = []
    baselines = []
    
    pred_records = []
    
    for r in backtest_rounds:
        # Train on rounds < r
        train_df = df[df['round'] < r].dropna(subset=[target_col] + feature_cols)
        # Test on round r (predicting round r+1 points)
        test_df = df[df['round'] == r].copy()
        
        # Keep only test rows that have a valid target (next week's points)
        test_df = test_df.dropna(subset=[target_col])
        
        if len(train_df) == 0 or len(test_df) == 0:
            continue
            
        X_train = train_df[feature_cols]
        y_train = train_df[target_col]
        X_test = test_df[feature_cols]
        y_test = test_df[target_col]
        
        # Train LightGBM model
        model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
            verbose=-1
        )
        model.fit(X_train, y_train)
        
        # Predict
        preds = model.predict(X_test)
        
        # Baseline: last week's points (total_points in current gameweek r)
        base = test_df['total_points'].values
        
        predictions.extend(preds)
        actuals.extend(y_test.values)
        baselines.extend(base)
        
        # Record predictions for optimization check
        test_df['predicted_points'] = preds
        pred_records.append(test_df)
        
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    baselines = np.array(baselines)
    
    # Evaluate model
    model_mae = mean_absolute_error(actuals, predictions)
    model_rmse = root_mean_squared_error(actuals, predictions)
    
    # Evaluate baseline
    base_mae = mean_absolute_error(actuals, baselines)
    base_rmse = root_mean_squared_error(actuals, baselines)
    
    print("\n=== Backtest Evaluation ===")
    print(f"Model:    MAE = {model_mae:.4f}, RMSE = {model_rmse:.4f}")
    print(f"Baseline: MAE = {base_mae:.4f},  RMSE = {base_rmse:.4f}")
    
    # Verify model beats baseline
    if model_mae < base_mae:
        print("\nSUCCESS: LightGBM model beats the baseline on MAE!")
    else:
        print("\nWARNING: LightGBM model failed to beat the baseline on MAE. Iterating on features may be needed.")
        
    if model_rmse < base_rmse:
        print("SUCCESS: LightGBM model beats the baseline on RMSE!")
    else:
        print("WARNING: LightGBM model failed to beat the baseline on RMSE.")
        
    # Save backtest predictions
    df_preds = pd.concat(pred_records, ignore_index=True)
    preds_output_path = os.path.join(data_dir, "predictions.parquet")
    df_preds.to_parquet(preds_output_path, index=False)
    print(f"Saved backtest predictions to {preds_output_path} ({len(df_preds)} rows)")

if __name__ == "__main__":
    run_backtest()
