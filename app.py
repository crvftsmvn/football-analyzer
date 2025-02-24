from flask import Flask, render_template, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

def get_last_five_games_weight(df, team, current_md, current_season):
    try:
        weights = []
        games_found = 0
        
        if current_md == 1:
            # For matchday 1, look at previous season's last games
            current_year = int(current_season.split('-')[0])
            prev_season = f"{current_year-1}-{current_year}"
            
            prev_season_df = df[df['Season'] == prev_season].copy()
            if not prev_season_df.empty:
                max_md = prev_season_df['MD'].max()
                for md in range(max_md, max_md-5, -1):
                    if games_found >= 5:
                        break
                        
                    game = prev_season_df[
                        (prev_season_df['MD'] == md) & 
                        ((prev_season_df['Home'] == team) | (prev_season_df['Away'] == team))
                    ]
                    
                    if not game.empty:
                        game = game.iloc[0]
                        was_home = game['Home'] == team
                        ftr = int(float(game['FTR']))
                        
                        # Calculate weight
                        if ftr == 0:  # Draw
                            weights.append(10)
                        elif (ftr == 1 and was_home) or (ftr == 2 and not was_home):  # Win
                            weights.append(20)
                        else:  # Loss
                            weights.append(0)
                        
                        games_found += 1
        else:
            # For other matchdays, look at current season's previous games
            current_df = df[df['Season'] == current_season].copy()
            
            for md in range(current_md-1, current_md-6, -1):
                if games_found >= 5:
                    break
                    
                if md < 1:
                    weights.append(0)  # Pad with 0 if not enough games
                    continue
                    
                game = current_df[
                    (current_df['MD'] == md) & 
                    ((current_df['Home'] == team) | (current_df['Away'] == team))
                ]
                
                if not game.empty:
                    game = game.iloc[0]
                    was_home = game['Home'] == team
                    ftr = int(float(game['FTR']))
                    
                    # Calculate weight
                    if ftr == 0:  # Draw
                        weights.append(10)
                    elif (ftr == 1 and was_home) or (ftr == 2 and not was_home):  # Win
                        weights.append(20)
                    else:  # Loss
                        weights.append(0)
                    
                    games_found += 1
                else:
                    weights.append(0)  # No game found for this matchday
        
        # Pad with zeros if we don't have 5 games
        while len(weights) < 5:
            weights.append(0)
            
        return sum(weights), weights[:5]  # Return total and last 5 weights
        
    except Exception as e:
        print(f"Error calculating weights: {str(e)}")
        return 0, [0, 0, 0, 0, 0]

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
                return None, None, 0, [0, 0, 0, 0, 0]
                
            # Get the last matchday of previous season
            last_md = prev_season_df['MD'].max()
            print(f"Last matchday of previous season: {last_md}")
            
            prev_games = prev_season_df[
                (prev_season_df['MD'] == last_md) & 
                ((prev_season_df['Home'] == team) | (prev_season_df['Away'] == team))
            ]
            
            if prev_games.empty:
                print(f"No games found for {team} in matchday {last_md} of season {prev_season}")
                return None, None, 0, [0, 0, 0, 0, 0]
                
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
            return None, None, 0, [0, 0, 0, 0, 0]
            
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
            return None, None, 0, [0, 0, 0, 0, 0]
            
        # Calculate weights for last 5 games
        total_weight, weights = get_last_five_games_weight(df, team, current_md, current_season)
            
        return position, result, total_weight, weights
        
    except Exception as e:
        print(f"Error in get_previous_game_result: {str(e)}")
        print(f"Team: {team}, MD: {current_md}, Current Season: {current_season}")
        return None, None, 0, [0, 0, 0, 0, 0]

def are_odds_similar(odds1, odds2, threshold=0.05):
    """Check if two sets of odds are similar (within threshold) regardless of order"""
    if len(odds1) != len(odds2):
        return False
    # Sort both odds lists to compare regardless of order
    sorted1 = sorted(odds1)
    sorted2 = sorted(odds2)
    return all(abs(a - b) <= threshold for a, b in zip(sorted1, sorted2))

def are_weights_matching(weights1, weights2):
    """Check if two weight sequences are exactly the same after sorting"""
    try:
        # Extract total and sequence parts
        total1, seq1 = weights1.split(' ', 1)
        total2, seq2 = weights2.split(' ', 1)
        
        # Convert sequences to lists of integers and sort them
        seq1_list = [int(x.strip()) for x in seq1.split(',')]
        seq2_list = [int(x.strip()) for x in seq2.split(',')]
        
        # Compare totals and sorted sequences
        return int(total1) == int(total2) and sorted(seq1_list) == sorted(seq2_list)
    except Exception as e:
        print(f"Error comparing weights: {str(e)}")
        print(f"Weights1: {weights1}")
        print(f"Weights2: {weights2}")
        return False

def get_color_code(index):
    """Return a color code based on index"""
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink']
    return colors[index % len(colors)]

def find_matching_games(matches_data):
    """Find games with matching odds or weights and assign colors"""
    odds_groups = {}  # {odds_key: [game_indices]}
    weight_groups = {}  # {weights_key: [game_indices]}
    
    # First pass: collect all odds and weights
    for i, match in enumerate(matches_data):
        try:
            # Extract odds
            odds_str = match.split('[')[-1].strip(']')
            odds = tuple(sorted(float(x.strip()) for x in odds_str.split(',')))
            
            # Extract weights from both teams
            parts = match.split(' vs ')
            home_part = parts[0].split('[')[1].split(']')[0]
            away_part = parts[1].split('[')[1].split(']')[0]
            
            # Group by odds
            for key, indices in odds_groups.items():
                if are_odds_similar(odds, key):
                    indices.append(i)
                    break
            else:
                odds_groups[odds] = [i]
            
            # Group by weights
            for existing_key, indices in weight_groups.items():
                home_key, away_key = existing_key
                if (are_weights_matching(home_part, home_key) and are_weights_matching(away_part, away_key)) or \
                   (are_weights_matching(home_part, away_key) and are_weights_matching(away_part, home_key)):
                    indices.append(i)
                    break
            else:
                weight_groups[(home_part, away_part)] = [i]
            
        except Exception as e:
            print(f"Error processing match {i}: {str(e)}")
            print(f"Match string: {match}")
            continue
    
    # Filter groups to keep only those with multiple matches
    odds_groups = {k: v for k, v in odds_groups.items() if len(v) > 1}
    weight_groups = {k: v for k, v in weight_groups.items() if len(v) > 1}
    
    # Assign colors
    odds_colors = {i: get_color_code(idx) for idx, group in enumerate(odds_groups.values()) for i in group}
    weight_colors = {i: get_color_code(idx) for idx, group in enumerate(weight_groups.values()) for i in group}
    
    return odds_colors, weight_colors

def format_match_data(df_season, full_df):
    try:
        df_season = df_season.copy()
        df_season['MD'] = pd.to_numeric(df_season['MD'], errors='coerce')
        current_season = df_season['Season'].iloc[0]  # Get the current season
        df_season = df_season.sort_values('MD')
        formatted_data = {}
        
        max_matchday = int(df_season['MD'].max())
        
        for md in range(1, max_matchday + 1):
            try:
                md_games = df_season[df_season['MD'] == float(md)]
                if md_games.empty:
                    continue
                
                # Sort games by datetime and home team
                md_games['DateTime'] = pd.to_datetime(md_games['Date'])
                md_games = md_games.sort_values(['DateTime', 'Home'], ascending=[True, False])
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
                        
                        # Format match string
                        if md == 1:
                            # For matchday 1, always show previous results
                            home_pos, home_prev, home_weight, home_weights = get_previous_game_result(full_df, game['Home'], md, current_season)
                            away_pos, away_prev, away_weight, away_weights = get_previous_game_result(full_df, game['Away'], md, current_season)
                            
                            home_info = f"<{home_pos} {home_prev}>" if home_pos and home_prev else "<null null>"
                            away_info = f"<{away_pos} {away_prev}>" if away_pos and away_prev else "<null null>"
                            match_str = f"{home_info} [{home_weight} {', '.join(map(str, home_weights))}] {game['Home']} vs {away_info} [{away_weight} {', '.join(map(str, away_weights))}] {game['Away']} => "
                        else:
                            home_pos, home_prev, home_weight, home_weights = get_previous_game_result(df_season, game['Home'], md, current_season)
                            away_pos, away_prev, away_weight, away_weights = get_previous_game_result(df_season, game['Away'], md, current_season)
                            
                            home_info = f"<{home_pos} {home_prev}>" if home_pos and home_prev else ""
                            away_info = f"<{away_pos} {away_prev}>" if away_pos and away_prev else ""
                            match_str = f"{home_info} [{home_weight} {', '.join(map(str, home_weights))}] {game['Home']} vs {away_info} [{away_weight} {', '.join(map(str, away_weights))}] {game['Away']} => "
                        
                        result_map = {0: 'D', 1: 'H', 2: 'A'}
                        
                        # Add odds
                        hm_odd = float(game['HmOd']) if pd.notnull(game['HmOd']) else 0.0
                        dr_odd = float(game['DrOd']) if pd.notnull(game['DrOd']) else 0.0
                        aw_odd = float(game['AwOd']) if pd.notnull(game['AwOd']) else 0.0
                        
                        match_str += f"{result_map[ftr]} [{hm_odd:.2f}, {dr_odd:.2f}, {aw_odd:.2f}]"
                        matches.append(match_str)
                    except Exception as e:
                        print(f"Error processing match: {str(e)}")
                        continue
                
                if matches:
                    # Get timing data
                    md_games['DateOnly'] = pd.to_datetime(md_games['Date']).dt.date
                    timing = md_games.groupby('DateOnly').size().tolist()
                    
                    # Find matching games and get their colors
                    odds_colors, weight_colors = find_matching_games(matches)
                    
                    # Add color tags to matches
                    colored_matches = []
                    for i, match in enumerate(matches):
                        odds_color = odds_colors.get(i)
                        weight_color = weight_colors.get(i)
                        
                        if odds_color or weight_color:
                            # Split the match string to color the appropriate parts
                            parts = match.split(' => ')
                            teams_part = parts[0]
                            odds_part = parts[1]
                            
                            if weight_color:
                                # Color the weights sections
                                teams_part = f'<span style="background-color: {weight_color};">{teams_part}</span>'
                            
                            if odds_color:
                                # Color the odds section
                                odds_part = f'<span style="background-color: {odds_color};">{odds_part}</span>'
                            
                            colored_match = f"{teams_part} => {odds_part}"
                        else:
                            colored_match = match
                        
                        colored_matches.append(colored_match)
                    
                    formatted_data[f"Matchday {md}"] = {
                        'matches': colored_matches,
                        'summary': {
                            'timing': timing,
                            'question': h2h_results,
                            'out': current_results
                        }
                    }
            except Exception as e:
                print(f"Error processing matchday {md}: {str(e)}")
                continue
        
        return formatted_data
    except Exception as e:
        print(f"Error in format_match_data: {str(e)}")
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_data/<league>', methods=['GET'])
def get_data(league):
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        
        league_files = {
            "English Premier League": "EnglishPremierLeague.csv",
            "Italian Serie A": "ItalySerieA.csv",
            "Portugal Primeira League": "GoodPortugal.csv"
        }
        
        if league in league_files:
            file_path = os.path.join(base_dir, 'data', league_files[league])
            
            if not os.path.exists(file_path):
                return jsonify({"error": f"CSV file not found at {file_path}"})
            
            # Load all data
            full_df = pd.read_csv(file_path)
            print(f"Loaded data for {league}")
            print(f"Available seasons: {full_df['Season'].unique()}")
            
            # Get seasons
            seasons = sorted(full_df['Season'].unique().tolist())
            
            # Get the selected season from query parameter
            selected_season = request.args.get('season')
            
            if selected_season:
                print(f"Processing season: {selected_season}")
                # Filter for selected season but pass full DataFrame
                df_season = full_df[full_df['Season'] == selected_season].copy()
                formatted_data = format_match_data(df_season, full_df)  # Pass both DataFrames
            else:
                formatted_data = {}
            
            return jsonify({
                "seasons": seasons,
                "data": formatted_data
            })
            
        return jsonify({"error": "League not found"}), 404
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)