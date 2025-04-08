from flask import Flask, render_template, jsonify, request
import os
import pandas as pd
import numpy as np

app = Flask(__name__)

def get_team_position(team, date, df):
    """Calculate team's points based on completed matches before the current matchday in the same season."""
    try:
        # Get the season from the current date
        current_season = df[df['Date'] == date]['Season'].iloc[0]
        
        # Get all matches before the current date in the same season
        past_matches = df[
            (df['Date'] < date) & 
            (df['Season'] == current_season)
        ]
        
        # Initialize points
        points = 0
        
        # Calculate points from past matches
        for _, match in past_matches.iterrows():
            if match['Home'] == team:
                if match['FTR'] == '1':  # Home win
                    points += 3
                elif match['FTR'] == '0':  # Draw
                    points += 1
            elif match['Away'] == team:
                if match['FTR'] == '2':  # Away win
                    points += 3
                elif match['FTR'] == '0':  # Draw
                    points += 1
        
        return points
    except Exception as e:
        print(f"Error calculating team points for {team}: {str(e)}")
        return 0

def get_previous_game_result(df, team, current_date, current_season):
    """Get team's previous game result and location"""
    try:
        # Get all matches up to the current date
        past_matches = df[
            (df['Season'] == current_season) & 
            (df['Date'] < current_date) &
            ((df['Home'] == team) | (df['Away'] == team))
        ].sort_values('Date', ascending=False)
        
        if past_matches.empty:
            return None, None
        
        last_game = past_matches.iloc[0]
        was_home = last_game['Home'] == team
        ftr = last_game['FTR']
        
        # Determine result
        if was_home:
            if ftr == '1':
                result = 'W'
            elif ftr == '2':
                result = 'L'
            else:
                result = 'D'
        else:
            if ftr == '2':
                result = 'W'
            elif ftr == '1':
                result = 'L'
            else:
                result = 'D'
        
        location = 'H' if was_home else 'A'
        return result, location
    except Exception as e:
        print(f"Error getting previous game result: {str(e)}")
        return None, None

def get_matchday_goals(df, current_date, current_season, current_md, team):
    """Get total goals scored and conceded by a team on current matchday up to the current match"""
    try:
        # Get all matches on current matchday up to the current date
        current_matches = df[
            (df['Season'] == current_season) & 
            (df['MD'] == current_md) &
            (df['Date'] <= current_date)
        ]
        
        # Get matches where team is home
        home_matches = current_matches[current_matches['Home'] == team]
        # Get matches where team is away
        away_matches = current_matches[current_matches['Away'] == team]
        
        # Calculate goals scored and conceded
        goals_scored = home_matches['HomeG'].sum() + away_matches['AwayG'].sum()
        goals_conceded = home_matches['AwayG'].sum() + away_matches['HomeG'].sum()
        
        return {
            'scored': int(goals_scored),
            'conceded': int(goals_conceded)
        }
    except Exception as e:
        print(f"Error getting matchday goals for {team}: {str(e)}")
        return None

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

def format_match_data(df):
    try:
        print("Starting format_match_data")
        # Convert date to datetime, handle invalid dates
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Sort by date
        df = df.sort_values('Date')
        
        # Get unique seasons and convert to list of strings
        seasons = [str(season) for season in sorted(df['Season'].unique(), reverse=True) if pd.notna(season)]
        
        # Initialize result dictionary
        result = {
            'seasons': seasons,
            'matchdays': {}
        }
        
        # Process each season
        for season in seasons:
            season_data = df[df['Season'] == season]
            
            # Get unique matchdays and convert to list of integers, handle invalid values
            matchdays = []
            for md in sorted(season_data['MD'].unique()):
                try:
                    if pd.notna(md) and str(md).strip() != '-':
                        matchdays.append(int(float(md)))
                except:
                    continue
            
            # Initialize team stats dictionary for the season
            team_stats = {}
            
            # Process each matchday
            for matchday in matchdays:
                matchday_data = season_data[season_data['MD'] == matchday]
                
                # Initialize counters for results
                current_results = {'H': 0, 'A': 0, 'D': 0}  # home_wins, away_wins, draws
                h2h_results = {'H': 0, 'A': 0, 'D': 0}  # home_wins, away_wins, draws
                
                # Format matches for this matchday
                matches = []
                for _, game in matchday_data.iterrows():
                    try:
                        # Get basic match info
                        home_team = str(game['Home']).strip() if pd.notna(game['Home']) else "Unknown"
                        away_team = str(game['Away']).strip() if pd.notna(game['Away']) else "Unknown"
                        if home_team in ['-', ''] or away_team in ['-', '']:
                            continue
                            
                        current_date = game['Date']
                        if pd.isna(current_date):
                            continue
                        date = current_date.strftime('%Y-%m-%d %H:%M')
                        
                        # Initialize stats for teams if not already in dictionary
                        if home_team not in team_stats:
                            team_stats[home_team] = {
                                'points': 0,
                                'goals_scored': 0,
                                'goals_conceded': 0,
                                'prev_result': None,
                                'prev_loc': None,
                                'h2h_points': {},
                                'h2h_away_goals': {}
                            }
                        if away_team not in team_stats:
                            team_stats[away_team] = {
                                'points': 0,
                                'goals_scored': 0,
                                'goals_conceded': 0,
                                'prev_result': None,
                                'prev_loc': None,
                                'h2h_points': {},
                                'h2h_away_goals': {}
                            }
                        
                        # Convert FTR to proper format (1=H, 2=A, 0=D)
                        ftr = str(game['FTR']).strip() if pd.notna(game['FTR']) else '0'
                        if ftr in ['1', 'H']:
                            ftr = 'H'
                        elif ftr in ['2', 'A']:
                            ftr = 'A'
                        else:
                            ftr = 'D'
                            
                        # Update current results
                        current_results[ftr] += 1
                        
                        # Process head-to-head results
                        try:
                            h_score_str = str(game['hScre']).strip() if pd.notna(game['hScre']) else ''
                            if not h_score_str or h_score_str == '-' or h_score_str == 'nan':
                                h_home_goals = 0
                                h_away_goals = 0
                            else:
                                h_score = h_score_str.split('-')
                                if len(h_score) != 2:
                                    h_home_goals = 0
                                    h_away_goals = 0
                                else:
                                    try:
                                        h_home_goals = int(h_score[0].strip())
                                        h_away_goals = int(h_score[1].strip())
                                    except ValueError:
                                        h_home_goals = 0
                                        h_away_goals = 0
                            
                            if h_home_goals > h_away_goals:
                                h2h_results['H'] += 1
                                if away_team not in team_stats[home_team]['h2h_points']:
                                    team_stats[home_team]['h2h_points'][away_team] = 0
                                if home_team not in team_stats[away_team]['h2h_points']:
                                    team_stats[away_team]['h2h_points'][home_team] = 0
                                team_stats[home_team]['h2h_points'][away_team] += 3
                            elif h_home_goals < h_away_goals:
                                h2h_results['A'] += 1
                                if away_team not in team_stats[home_team]['h2h_points']:
                                    team_stats[home_team]['h2h_points'][away_team] = 0
                                if home_team not in team_stats[away_team]['h2h_points']:
                                    team_stats[away_team]['h2h_points'][home_team] = 0
                                team_stats[away_team]['h2h_points'][home_team] += 3
                            else:
                                h2h_results['D'] += 1
                                if away_team not in team_stats[home_team]['h2h_points']:
                                    team_stats[home_team]['h2h_points'][away_team] = 0
                                if home_team not in team_stats[away_team]['h2h_points']:
                                    team_stats[away_team]['h2h_points'][home_team] = 0
                                team_stats[home_team]['h2h_points'][away_team] += 1
                                team_stats[away_team]['h2h_points'][home_team] += 1
                            
                            # Update h2h away goals
                            if away_team not in team_stats[home_team]['h2h_away_goals']:
                                team_stats[home_team]['h2h_away_goals'][away_team] = 0
                            if home_team not in team_stats[away_team]['h2h_away_goals']:
                                team_stats[away_team]['h2h_away_goals'][home_team] = 0
                            team_stats[away_team]['h2h_away_goals'][home_team] += h_away_goals
                        except Exception as e:
                            print(f"Error processing h2h score: {e}")
                            print(f"hScre value that caused error: {game['hScre']}")
                            continue
                        
                        # Get odds and convert to float, handle missing values
                        hm_odd = float(game['HmOd']) if pd.notna(game['HmOd']) and str(game['HmOd']).strip() != '-' else 0.0
                        dr_odd = float(game['DrOd']) if pd.notna(game['DrOd']) and str(game['DrOd']).strip() != '-' else 0.0
                        aw_odd = float(game['AwOd']) if pd.notna(game['AwOd']) and str(game['AwOd']).strip() != '-' else 0.0
                        
                        # Get hRnd value and convert to int, handle missing values
                        try:
                            h_rnd_str = str(game['hRnd']).strip() if pd.notna(game['hRnd']) else ''
                            h_rnd = int(float(h_rnd_str)) if h_rnd_str and h_rnd_str != '-' else 0
                        except:
                            h_rnd = 0
                        
                        # Calculate positions before this match
                        teams = list(team_stats.keys())
                        positions = {}
                        
                        # Sort teams by points, goal difference, goals scored, h2h points, and h2h away goals
                        sorted_teams = sorted(teams, key=lambda x: (
                            -team_stats[x]['points'],
                            -(team_stats[x]['goals_scored'] - team_stats[x]['goals_conceded']),
                            -team_stats[x]['goals_scored'],
                            -sum(team_stats[x]['h2h_points'].values()),
                            -sum(team_stats[x]['h2h_away_goals'].values())
                        ))
                        
                        # Assign positions
                        for i, team in enumerate(sorted_teams, 1):
                            positions[team] = i
                        
                        # Create match object with additional stats
                        match = {
                            'date': date,
                            'home_team': home_team,
                            'away_team': away_team,
                            'result': ftr,
                            'odds': {
                                'home': hm_odd,
                                'draw': dr_odd,
                                'away': aw_odd
                            },
                            'h_rnd': h_rnd,
                            'home_points': team_stats[home_team]['points'],
                            'away_points': team_stats[away_team]['points'],
                            'home_position': positions[home_team],
                            'away_position': positions[away_team],
                            'home_goals_scored': team_stats[home_team]['goals_scored'],
                            'home_goals_conceded': team_stats[home_team]['goals_conceded'],
                            'away_goals_scored': team_stats[away_team]['goals_scored'],
                            'away_goals_conceded': team_stats[away_team]['goals_conceded'],
                            'home_prev_result': team_stats[home_team]['prev_result'],
                            'home_prev_loc': team_stats[home_team]['prev_loc'],
                            'away_prev_result': team_stats[away_team]['prev_result'],
                            'away_prev_loc': team_stats[away_team]['prev_loc']
                        }
                        matches.append(match)
                        
                        # Update stats after the match
                        if ftr == 'H':  # Home win
                            team_stats[home_team]['points'] += 3
                            team_stats[home_team]['prev_result'] = 'W'
                            team_stats[home_team]['prev_loc'] = 'H'
                            team_stats[away_team]['prev_result'] = 'L'
                            team_stats[away_team]['prev_loc'] = 'A'
                        elif ftr == 'A':  # Away win
                            team_stats[away_team]['points'] += 3
                            team_stats[away_team]['prev_result'] = 'W'
                            team_stats[away_team]['prev_loc'] = 'A'
                            team_stats[home_team]['prev_result'] = 'L'
                            team_stats[home_team]['prev_loc'] = 'H'
                        else:  # Draw
                            team_stats[home_team]['points'] += 1
                            team_stats[away_team]['points'] += 1
                            team_stats[home_team]['prev_result'] = 'D'
                            team_stats[home_team]['prev_loc'] = 'H'
                            team_stats[away_team]['prev_result'] = 'D'
                            team_stats[away_team]['prev_loc'] = 'A'
                        
                        # Update goals
                        team_stats[home_team]['goals_scored'] += h_home_goals
                        team_stats[home_team]['goals_conceded'] += h_away_goals
                        team_stats[away_team]['goals_scored'] += h_away_goals
                        team_stats[away_team]['goals_conceded'] += h_home_goals
                        
                    except Exception as e:
                        print(f"Error processing match: {str(e)}")
                        print(f"Match data that caused error: {game}")
                        continue
                
                # Get timing data
                timing = []
                # Group by date only (ignoring time)
                date_groups = matchday_data['Date'].dt.date.unique()
                for date in date_groups:
                    # Count matches for this date
                    matches_on_date = len(matchday_data[matchday_data['Date'].dt.date == date])
                    timing.append(matches_on_date)
                
                # Get rounds data
                rounds = []
                for x in matchday_data['hRnd'].unique().tolist():
                    try:
                        if pd.notna(x) and str(x).strip() != '-':
                            rounds.append(int(float(x)))
                    except:
                        continue
                rounds = sorted(rounds)
                rounds_str = f"Rounds[{','.join(map(str, rounds))}]"
                
                # Create matchday object
                matchday_key = f"{season}-{matchday:02d}"  # Pad matchday with leading zeros
                result['matchdays'][matchday_key] = {
                    'season': season,
                    'matchday': matchday,
                    'matches': matches,
                    'timing': timing,
                    'rounds': rounds_str,
                    'question': [int(h2h_results['H']), int(h2h_results['A']), int(h2h_results['D'])],
                    'out': [int(current_results['H']), int(current_results['A']), int(current_results['D'])]
                }
                print(f"Processed matchday {matchday_key}")
                print(f"Question: {h2h_results}")
                print(f"Answer: {current_results}")
        
        # Sort matchdays by season and matchday number
        sorted_matchdays = {}
        for key in sorted(result['matchdays'].keys(), key=lambda x: (x.split('-')[0], int(x.split('-')[1]))):
            sorted_matchdays[key] = result['matchdays'][key]
        
        result['matchdays'] = sorted_matchdays
        print("Successfully completed format_match_data")
        return result
        
    except Exception as e:
        print(f"Error in format_match_data: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

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
            "German Bundesliga": "GermanBundesliga.csv",
            "Italian Serie A": "ItalySerieA.csv",
            "Turkish Super League": "TurkishSuperLeague.csv",
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
                print("Sample data:")
                print(full_df.head())
                
                # Check required columns
                required_columns = ['Date', 'MD', 'Home', 'Away', 'FTR', 'hScre', 'hRnd', 'Season']
                missing_columns = [col for col in required_columns if col not in full_df.columns]
                if missing_columns:
                    print(f"Missing required columns: {missing_columns}")
                    return jsonify({"error": f"Missing required columns: {missing_columns}"}), 400
                
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
                formatted_data = format_match_data(df_season)
            else:
                # If no season is selected, format all data
                print("No season selected, processing all data")
                formatted_data = format_match_data(full_df)
            
            # Check if formatted_data is None or invalid
            if not formatted_data or 'matchdays' not in formatted_data:
                print("Error: formatted_data is None or invalid")
                print(f"formatted_data: {formatted_data}")
                return jsonify({"error": "Error processing match data"}), 500
            
            # Debug print the formatted data
            print("Formatted data sample:")
            if formatted_data and 'matchdays' in formatted_data:
                for key, value in list(formatted_data['matchdays'].items())[:1]:
                    print(f"Matchday {key}:")
                    print(f"Matches: {value['matches'][:1] if value['matches'] else 'No matches'}")
            
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
                    print("Sample data:")
                    print(full_df.head())
                    
                    # Get seasons
                    seasons = sorted(full_df['Season'].unique().tolist())
                    
                    # Get the selected season from query parameter
                    selected_season = request.args.get('season')
                    
                    if selected_season:
                        print(f"Processing season: {selected_season}")
                        df_season = full_df[full_df['Season'] == selected_season].copy()
                        formatted_data = format_match_data(df_season)
                    else:
                        # If no season is selected, format all data
                        print("No season selected, processing all data")
                        formatted_data = format_match_data(full_df)
                    
                    # Debug print the formatted data
                    print("Formatted data sample:")
                    if formatted_data and 'matchdays' in formatted_data:
                        for key, value in list(formatted_data['matchdays'].items())[:1]:
                            print(f"Matchday {key}:")
                            print(f"Matches: {value['matches'][:1] if value['matches'] else 'No matches'}")
                    
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