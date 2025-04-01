from flask import Flask, render_template, jsonify, request
import os
import pandas as pd
import numpy as np

app = Flask(__name__)

def get_previous_game_result(df, team, current_md, current_season):
    try:
        if current_md == 1:
            # Parse current season years (e.g., "2022-2023" -> 2022)
            current_year = int(current_season.split('-')[0])
            prev_season = f"{current_year-1}-{current_year}"
            
            print(f"Looking for {team} in previous season: {prev_season}")
            print(f"Available seasons: {df['Season'].unique()}")
            
            # Get data from previous season's last matchday
            prev_season_df = df[df['Season'] == prev_season].copy()
            
            if prev_season_df.empty:
                print(f"No data found for previous season: {prev_season}")
                return None, None
                
            # Get the last matchday of previous season
            last_md = prev_season_df['MD'].max()
            print(f"Last matchday of previous season: {last_md}")
            
            prev_games = prev_season_df[
                (prev_season_df['MD'] == last_md) & 
                ((prev_season_df['Home'] == team) | (prev_season_df['Away'] == team))
            ]
            
            if prev_games.empty:
                print(f"No games found for {team} in matchday {last_md} of season {prev_season}")
                return None, None
                
            print(f"Found previous game for {team}: {prev_games.iloc[0]['Home']} vs {prev_games.iloc[0]['Away']}")
        else:
            # For other matchdays, look at current season's previous games
            current_season_df = df[df['Season'] == current_season].copy()
            current_season_df['MD'] = pd.to_numeric(current_season_df['MD'], errors='coerce')
            
            prev_games = current_season_df[
                (current_season_df['MD'].notna()) &
                (current_season_df['MD'] < current_md) & 
                ((current_season_df['Home'] == team) | (current_season_df['Away'] == team))
            ].sort_values('MD', ascending=False)
        
        if prev_games.empty:
            return None, None
            
        last_game = prev_games.iloc[0]
        was_home = last_game['Home'] == team
        position = 'H' if was_home else 'A'
        
        try:
            ftr = int(float(last_game['FTR']))
            if ftr == 0:
                result = 'D'
            elif ftr == 1:
                result = 'W' if was_home else 'L'
            else:  # ftr == 2
                result = 'L' if was_home else 'W'
        except (ValueError, TypeError):
            print(f"Invalid FTR value: {last_game['FTR']}")
            return None, None
            
        return position, result
        
    except Exception as e:
        print(f"Error in get_previous_game_result: {str(e)}")
        print(f"Team: {team}, MD: {current_md}, Current Season: {current_season}")
        return None, None

def are_odds_similar(odds1, odds2, threshold=0.05):
    """Check if two sets of odds are similar (within threshold) regardless of order"""
    if len(odds1) != len(odds2):
        return False
    # Sort both odds lists to compare regardless of order
    sorted1 = sorted(odds1)
    sorted2 = sorted(odds2)
    return all(abs(a - b) <= threshold for a, b in zip(sorted1, sorted2))

def get_color_code(index):
    """Return a color code based on index"""
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink']
    return colors[index % len(colors)]

def find_matching_games(matches_data):
    """Find games with matching odds and assign colors"""
    odds_groups = {}  # {odds_key: [game_indices]}
    
    # Collect all odds
    for i, match in enumerate(matches_data):
        try:
            # Extract odds from the last bracket in the string
            parts = match.split(' => ')
            if len(parts) < 2:
                continue
                
            result_part = parts[1]
            if '[' not in result_part:
                continue
                
            odds_str = result_part.split('[')[-1].strip(']')
            odds = tuple(sorted(float(x.strip()) for x in odds_str.split(',')))
            
            # Group by odds
            for key, indices in odds_groups.items():
                if are_odds_similar(odds, key):
                    indices.append(i)
                    break
            else:
                odds_groups[odds] = [i]
            
        except Exception as e:
            print(f"Error processing match {i}: {str(e)}")
            print(f"Match string: {match}")
            continue
    
    # Filter groups to keep only those with multiple matches
    odds_groups = {k: v for k, v in odds_groups.items() if len(v) > 1}
    
    # Assign colors
    odds_colors = {i: get_color_code(idx) for idx, group in enumerate(odds_groups.values()) for i in group}
    
    return odds_colors

def format_match_data(df_season, full_df):
    try:
        # Create a deep copy to avoid SettingWithCopyWarning
        df_season = df_season.copy(deep=True)
        df_season['MD'] = pd.to_numeric(df_season['MD'], errors='coerce')
        current_season = df_season['Season'].iloc[0]  # Get the current season
        df_season = df_season.sort_values('MD')
        formatted_data = {}
        
        max_matchday = int(df_season['MD'].max())
        
        for md in range(1, max_matchday + 1):
            try:
                md_games = df_season[df_season['MD'] == float(md)].copy(deep=True)  # Create a copy here
                if md_games.empty:
                    continue
                
                # Sort games by datetime and home team (both ascending)
                md_games.loc[:, 'DateTime'] = pd.to_datetime(md_games['Date'])  # Use .loc to avoid warning
                md_games = md_games.sort_values(['DateTime', 'Home'], ascending=[True, True])
                matches = []
                
                # Initialize counters for results
                current_results = [0, 0, 0]  # [home_wins, away_wins, draws]
                h2h_results = [0, 0, 0]  # [home_wins, away_wins, draws]
                
                for _, game in md_games.iterrows():
                    try:
                        # Process match result
                        ftr = int(float(game['FTR']))
                        
                        # Update current results
                        if ftr == 1:  # Home win
                            current_results[0] += 1
                        elif ftr == 2:  # Away win
                            current_results[1] += 1
                        else:  # Draw
                            current_results[2] += 1
                        
                        # Process head-to-head results
                        try:
                            if pd.notnull(game['hScre']):
                                scores = str(game['hScre']).split('-')
                                home_score = int(float(scores[0]))
                                away_score = int(float(scores[1]))
                                
                                if home_score > away_score:
                                    h2h_results[0] += 1
                                elif home_score < away_score:
                                    h2h_results[1] += 1
                                else:
                                    h2h_results[2] += 1
                        except:
                            pass  # Skip if h2h score processing fails
                        
                        # Format date and time
                        try:
                            # Get date from the Date column
                            if 'Date' in game and pd.notnull(game['Date']):
                                date_str = str(game['Date'])
                                
                                # Try to get time information
                                time_str = ""
                                if 'Time' in game and pd.notnull(game['Time']):
                                    time_str = str(game['Time'])
                                elif 'DateTime' in game and pd.notnull(game['DateTime']):
                                    # If we have a DateTime column, extract the time part
                                    time_str = str(game['DateTime'].time())
                                else:
                                    # If no time is available, use a default time
                                    time_str = "15:00"  # Default to 3 PM
                                
                                # Format with both date and time
                                date_time_str = f"DATE_INFO:{date_str} {time_str}"
                            else:
                                date_time_str = "DATE_INFO:Unknown Unknown"
                            
                            # Format with a distinctive prefix that won't be confused with other brackets
                            date_time_str = f"<<{date_time_str}>>"
                            print(f"Adding date and time: {date_time_str} to match")  # Debug print
                        except Exception as e:
                            print(f"Error formatting date/time: {str(e)}")
                            date_time_str = "<<DATE_INFO:Unknown Unknown>>"
                        
                        # Get previous game results without weights
                        if md == 1:
                            # For matchday 1, always show previous results
                            home_pos, home_prev = get_previous_game_result(full_df, game['Home'], md, current_season)
                            away_pos, away_prev = get_previous_game_result(full_df, game['Away'], md, current_season)
                            
                            home_info = f"<{home_pos} {home_prev}>" if home_pos and home_prev else "<null null>"
                            away_info = f"<{away_pos} {away_prev}>" if away_pos and away_prev else "<null null>"
                            match_str = f"{date_time_str}{home_info} {game['Home']} vs {away_info} {game['Away']} => "
                        else:
                            home_pos, home_prev = get_previous_game_result(df_season, game['Home'], md, current_season)
                            away_pos, away_prev = get_previous_game_result(df_season, game['Away'], md, current_season)
                            
                            home_info = f"<{home_pos} {home_prev}>" if home_pos and home_prev else ""
                            away_info = f"<{away_pos} {away_prev}>" if away_pos and away_prev else ""
                            match_str = f"{date_time_str}{home_info} {game['Home']} vs {away_info} {game['Away']} => "
                        
                        result_map = {0: 'D', 1: 'H', 2: 'A'}
                        
                        # Add odds
                        hm_odd = float(game['HmOd']) if pd.notnull(game['HmOd']) else 0.0
                        dr_odd = float(game['DrOd']) if pd.notnull(game['DrOd']) else 0.0
                        aw_odd = float(game['AwOd']) if pd.notnull(game['AwOd']) else 0.0
                        
                        # Get hRnd value
                        h_rnd = int(float(game['hRnd'])) if pd.notnull(game['hRnd']) else 0
                        
                        match_str += f"{result_map[ftr]} [{hm_odd:.2f}, {dr_odd:.2f}, {aw_odd:.2f}] <span class='h-rnd'>[{h_rnd}]</span>"
                        matches.append(match_str)
                    except Exception as e:
                        print(f"Error processing match: {str(e)}")
                        continue
                
                if matches:
                    # Get timing data
                    md_games['DateOnly'] = pd.to_datetime(md_games['Date']).dt.date
                    timing = md_games.groupby('DateOnly').size().tolist()
                    
                    # Get distinct round numbers from hRnd column
                    rounds = sorted(md_games['hRnd'].unique().tolist())
                    # Convert to integers and remove any decimal places
                    rounds = [int(float(round_num)) for round_num in rounds]
                    rounds_str = f"Rounds [{len(rounds)}][{', '.join(map(str, rounds))}]"
                    
                    # Find matching games but don't use their colors
                    odds_colors = find_matching_games(matches)
                    
                    # Format the matchday data
                    formatted_data[md] = {
                        'matches': matches,
                        'timing': timing,
                        'odds_colors': odds_colors,
                        'rounds': rounds_str,
                        'question': h2h_results,
                        'out': current_results
                    }
            except Exception as e:
                print(f"Error processing matchday {md}: {str(e)}")
                continue
        
        return formatted_data
    except Exception as e:
        print(f"Error in format_match_data: {str(e)}")
        raise

@app.route('/test')
def test():
    return "App is running correctly!"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data/<league>', methods=['GET'])
def get_data(league):
    try:
        # Get the directory where the script is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data')
        
        print(f"Base directory: {base_dir}")
        print(f"Data directory: {data_dir}")
        print(f"Current working directory: {os.getcwd()}")
        
        league_files = {
            "English Premier League": "EnglishPremierLeague.csv",
            "Italian Serie A": "ItalySerieA.csv",
            "Portugal Primeira League": "GoodPortugal.csv"
        }
        
        if league in league_files:
            file_path = os.path.join(data_dir, league_files[league])
            print(f"Looking for file at: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"File not found at {file_path}")
                print(f"Directory contents of {data_dir}:")
                try:
                    print(os.listdir(data_dir))
                except Exception as e:
                    print(f"Error listing directory: {str(e)}")
                return jsonify({"error": "Data file not found"}), 404
            
            try:
                full_df = pd.read_csv(file_path)
                print(f"Successfully loaded {league} data")
            except Exception as e:
                print(f"Error reading CSV: {str(e)}")
                return jsonify({"error": f"Error reading data: {str(e)}"}), 500
            
            # Get seasons
            seasons = sorted(full_df['Season'].unique().tolist())
            
            # Get the selected season from query parameter
            selected_season = request.args.get('season')
            
            if selected_season:
                print(f"Processing season: {selected_season}")
                df_season = full_df[full_df['Season'] == selected_season].copy()
                formatted_data = format_match_data(df_season, full_df)
            else:
                formatted_data = {}
            
            return jsonify({
                "seasons": seasons,
                "data": formatted_data
            })
            
        elif league == 'German Bundesliga':
            file_path = os.path.join(data_dir, 'GermanBundesliga.csv')
            print(f"Looking for file at: {file_path}")
            if os.path.exists(file_path):
                try:
                    full_df = pd.read_csv(file_path)
                    print("Successfully loaded German Bundesliga data")
                    
                    # Get seasons
                    seasons = sorted(full_df['Season'].unique().tolist())
                    
                    # Get the selected season from query parameter
                    selected_season = request.args.get('season')
                    
                    if selected_season:
                        print(f"Processing season: {selected_season}")
                        df_season = full_df[full_df['Season'] == selected_season].copy()
                        formatted_data = format_match_data(df_season, full_df)
                    else:
                        formatted_data = {}
                    
                    return jsonify({
                        "seasons": seasons,
                        "data": formatted_data
                    })
                except Exception as e:
                    print(f"Error processing German Bundesliga data: {str(e)}")
                    return jsonify({"error": f"Error processing data: {str(e)}"}), 500
            else:
                print(f"File not found: {file_path}")
                return jsonify({'error': 'League not found'})
            
        return jsonify({"error": "League not found"}), 404
        
    except Exception as e:
        print(f"Error in get_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use the PORT environment variable provided by Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)