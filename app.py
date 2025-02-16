from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

def get_previous_game_result(df, team, current_md):
    # Previous implementation remains the same
    if current_md == 1:
        return None, None
        
    prev_games = df[
        (df['MD'] < current_md) & 
        ((df['Home'] == team) | (df['Away'] == team))
    ].sort_values('MD', ascending=False)
    
    if prev_games.empty:
        return None, None
        
    last_game = prev_games.iloc[0]
    was_home = last_game['Home'] == team
    position = 'H' if was_home else 'A'
    
    ftr = int(last_game['FTR'])
    if ftr == 0:
        result = 'D'
    elif ftr == 1:
        result = 'W' if was_home else 'L'
    else:
        result = 'L' if was_home else 'W'
        
    return position, result



def format_match_data(df):
    df = df.sort_values('MD')
    formatted_data = {}
    
    max_matchday = int(df['MD'].max())
    
    for md in range(1, max_matchday + 1):
        md_games = df[df['MD'] == md]
        matches = []
        
        for _, game in md_games.iterrows():
            try:
                # Validate FTR value first
                try:
                    ftr = int(game['FTR'])
                    if ftr not in [0, 1, 2]:
                        continue  # Skip this match if FTR is not 0, 1, or 2
                except (ValueError, TypeError):
                    continue  # Skip if FTR can't be converted to int
                
                if md == 1:
                    match_str = f"{game['Home']} vs {game['Away']} => "
                else:
                    home_pos, home_prev = get_previous_game_result(df, game['Home'], md)
                    away_pos, away_prev = get_previous_game_result(df, game['Away'], md)
                    
                    home_info = f"<{home_pos} {home_prev}>" if home_pos and home_prev else ""
                    away_info = f"<{away_pos} {away_prev}>" if away_pos and home_prev else ""
                    match_str = f"{home_info} {game['Home']} vs {away_info} {game['Away']} => "
                
                result_map = {0: 'D', 1: 'H', 2: 'A'}
                
                # Add error checking for odds columns
                hm_odd = float(game['HmOd']) if pd.notnull(game['HmOd']) else 0.0
                dr_odd = float(game['DrOd']) if pd.notnull(game['DrOd']) else 0.0
                aw_odd = float(game['AwOd']) if pd.notnull(game['AwOd']) else 0.0
                
                match_str += f"{result_map[ftr]} [{hm_odd:.2f}, {dr_odd:.2f}, {aw_odd:.2f}]"
                matches.append(match_str)
            except Exception as e:
                print(f"Error processing match: {str(e)}")
                print(f"Game data: {game}")
                continue
        
        if matches:
            # Extract just the date part and count games per date
            md_games['DateOnly'] = pd.to_datetime(md_games['Date']).dt.date
            timing = md_games.groupby('DateOnly').size().tolist()
            
            # Process head-to-head results
            h2h_results = [0, 0, 0]  # [home_wins, away_wins, draws]
            for _, game in md_games.iterrows():
                try:
                    score_str = str(game['hScre'])
                    if '-' in score_str:
                        scores = score_str.split('-')
                        home_score = int(float(scores[0]))
                        away_score = int(float(scores[1]))
                        if home_score > away_score:
                            h2h_results[0] += 1
                        elif home_score < away_score:
                            h2h_results[1] += 1
                        else:
                            h2h_results[2] += 1
                except Exception as e:
                    print(f"Error processing score {game['hScre']}: {str(e)}")
                    continue
            
            # Get current matchday results
            current_results = [0, 0, 0]  # [home_wins, away_wins, draws]
            for _, game in md_games.iterrows():
                ftr = int(game['FTR'])
                if ftr == 1:
                    current_results[0] += 1
                elif ftr == 2:
                    current_results[1] += 1
                else:
                    current_results[2] += 1
            
            formatted_data[f"Matchday {md}"] = {
                'matches': matches,
                'summary': {
                    'timing': timing,
                    'question': h2h_results,
                    'out': current_results
                }
            }
    
    return formatted_data



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_data/<league>')
def get_data(league):
    try:
        if league == "English Premier League":
            # Get the absolute path to the data directory
            base_dir = os.path.abspath(os.path.dirname(__file__))
            file_path = os.path.join(base_dir, 'data', 'GoodPrem.csv')
            
            if not os.path.exists(file_path):
                return jsonify({"error": f"CSV file not found at {file_path}"})
            
            df = pd.read_csv(file_path)
            formatted_data = format_match_data(df)
            return jsonify(formatted_data)
        return jsonify({"error": "Data not available for this league yet"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)