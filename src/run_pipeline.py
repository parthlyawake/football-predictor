import subprocess
import sys
import os

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_script(script_name):
    script_path = os.path.join(workspace_dir, "src", script_name)
    print(f"\n=========================================")
    print(f"RUNNING: {script_name}")
    print(f"=========================================")
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    if result.returncode != 0:
        print(f"ERROR: {script_name} failed with exit code {result.returncode}!")
        sys.exit(result.returncode)
    print(f"FINISHED: {script_name} successfully.")

def main():
    print("Starting Fantasy Football Predictor Pipeline...")
    
    # Pre-processing: Refresh results with live/completed scores
    run_script("refresh_results.py")
    
    # Phase 1: Data Cleaning and Identity Matching
    run_script("clean_data.py")
    
    # Phase 2: Feature Engineering
    run_script("feature_engineering.py")
    
    # Phase 2: Model Training & Backtesting
    run_script("train_predict.py")
    
    # Phase 3: Team Optimizer (optimizing for gameweek 30 as a test case)
    run_script("optimizer.py")
    
    # Pre-processing Track B: Parse official FIFA squad list PDF
    run_script("parse_squads.py")
    
    # Phase 4: Track B (World Cup 2026) Model and Optimizer
    run_script("track_b_model.py")
    
    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()
