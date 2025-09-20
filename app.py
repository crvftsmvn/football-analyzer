from flask import Flask, render_template, request, jsonify
import os
import pandas as pd

app = Flask(__name__)

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_seasons')
def get_seasons():
    league = request.args.get('league')
    if not league:
        return jsonify({'error': 'No league specified'}), 400
    csv_path = os.path.join(DATA_FOLDER, league)
    if not os.path.exists(csv_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        df = pd.read_csv(csv_path)
        if 'Season' not in df.columns:
            return jsonify({'error': 'No Season column in file'}), 400
        seasons = sorted(df['Season'].dropna().unique().tolist())
        return jsonify({'seasons': seasons})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_matchday_vectors')
def get_matchday_vectors():
    league = request.args.get('league')
    season = request.args.get('season')
    if not league or not season:
        return jsonify({'error': 'Missing league or season'}), 400
    csv_path = os.path.join(DATA_FOLDER, league)
    if not os.path.exists(csv_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        df = pd.read_csv(csv_path)
        if 'Season' not in df.columns or 'MD' not in df.columns or 'FTR' not in df.columns or 'hScre' not in df.columns:
            return jsonify({'error': 'Required columns missing'}), 400
        df = df[df['Season'] == season]
        matchdays = sorted(df['MD'].dropna().unique(), key=lambda x: int(x))
        md_vectors = {}
        for md in matchdays:
            sub = df[df['MD'] == md]
            # FTR counts
            home = int((sub['FTR'] == 1).sum())
            away = int((sub['FTR'] == 2).sum())
            draw = int((sub['FTR'] == 0).sum())
            # hScre counts
            h_home = h_away = h_draw = 0
            for val in sub['hScre'].dropna():
                try:
                    hs, as_ = [int(x) for x in str(val).split('-')]
                    if hs > as_:
                        h_home += 1
                    elif hs < as_:
                        h_away += 1
                    else:
                        h_draw += 1
                except Exception:
                    continue
            md_vectors[int(md)] = {
                'vector': [home, away, draw],
                'hScre_vector': [h_home, h_away, h_draw]
            }
        # Calculate game frequency for each matchday
        md_game_frequency = {}
        for md in matchdays:
            md_matches = df[df['MD'] == md]
            game_frequency = []
            if 'Date_Only' in md_matches.columns:
                # Group by Date_Only and count games per day
                date_counts = md_matches['Date_Only'].value_counts().sort_index()
                game_frequency = date_counts.tolist()
            elif 'Date' in md_matches.columns:
                # Extract date part from datetime and count games per day
                md_matches_copy = md_matches.copy()
                md_matches_copy['Date_Only'] = pd.to_datetime(md_matches_copy['Date']).dt.date
                date_counts = md_matches_copy['Date_Only'].value_counts().sort_index()
                game_frequency = date_counts.tolist()
            else:
                # If no date information, assume all games on same day
                game_frequency = [len(md_matches)]
            md_game_frequency[int(md)] = game_frequency

        # Arrange into 5 rows as described
        grid = [[] for _ in range(5)]
        for idx, md in enumerate(matchdays):
            row = (int(md)-1) % 5
            grid[row].append({
                'matchday': int(md),
                'vector': md_vectors[int(md)]['vector'],
                'hScre_vector': md_vectors[int(md)]['hScre_vector'],
                'game_frequency': md_game_frequency[int(md)]
            })
        return jsonify({'grid': grid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_matchday_details')
def get_matchday_details():
    league = request.args.get('league')
    season = request.args.get('season')
    if not league or not season:
        return jsonify({'error': 'Missing league or season'}), 400
    csv_path = os.path.join(DATA_FOLDER, league)
    if not os.path.exists(csv_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        df = pd.read_csv(csv_path)
        if 'Season' not in df.columns or 'MD' not in df.columns or 'FTR' not in df.columns or 'Home' not in df.columns or 'Away' not in df.columns:
            return jsonify({'error': 'Required columns missing'}), 400
        df = df[df['Season'] == season].copy()
        df = df.sort_values(['MD', 'Date' if 'Date' in df.columns else 'MD'])
        # Build a list of matchdays
        matchdays = sorted(df['MD'].dropna().unique(), key=lambda x: int(x))
        # For each team, build a list of their games (with index)
        team_games = {}
        for idx, row in df.iterrows():
            for team, loc in [(row['Home'], 'H'), (row['Away'], 'A')]:
                if team not in team_games:
                    team_games[team] = []
                team_games[team].append({
                    'idx': idx,
                    'MD': row['MD'],
                    'FTR': row['FTR'],
                    'loc': loc,
                    'opp': row['Away'] if loc == 'H' else row['Home'],
                    'date': row['Date'] if 'Date' in row else None
                })
        # For each matchday, for each match, gather info
        result = []
        for md in matchdays:
            md_matches = df[df['MD'] == md]
            
            # Calculate game frequency for this matchday
            game_frequency = []
            if 'Date_Only' in md_matches.columns:
                # Group by Date_Only and count games per day
                date_counts = md_matches['Date_Only'].value_counts().sort_index()
                game_frequency = date_counts.tolist()
            elif 'Date' in md_matches.columns:
                # Extract date part from datetime and count games per day
                md_matches_copy = md_matches.copy()
                md_matches_copy['Date_Only'] = pd.to_datetime(md_matches_copy['Date']).dt.date
                date_counts = md_matches_copy['Date_Only'].value_counts().sort_index()
                game_frequency = date_counts.tolist()
            else:
                # If no date information, assume all games on same day
                game_frequency = [len(md_matches)]
            
            matches = []
            for _, match in md_matches.iterrows():
                home = match['Home']
                away = match['Away']
                # Find this match's index in team_games
                home_games = team_games[home]
                away_games = team_games[away]
                # Find this match in the sequence for each team
                home_idx = next((i for i, g in enumerate(home_games) if g['MD'] == md and g['loc'] == 'H' and g['opp'] == away), None)
                away_idx = next((i for i, g in enumerate(away_games) if g['MD'] == md and g['loc'] == 'A' and g['opp'] == home), None)
                # Previous game info
                def prev_game_info(games, idx):
                    if idx is not None and idx > 0:
                        prev = games[idx-1]
                        return {
                            'FTR': prev['FTR'],
                            'loc': prev['loc'],
                            'opp': prev['opp'],
                            'MD': prev['MD']
                        }
                    return None
                home_prev = prev_game_info(home_games, home_idx)
                away_prev = prev_game_info(away_games, away_idx)
                # Last 5 and 7 games info
                def last_games_info(games, idx, n):
                    if idx is None:
                        return {'FTR_seq': [], 'perc': 0}
                    seq = [g['FTR'] for g in games[max(0, idx-n):idx]]
                    # Convert FTR to points
                    if n == 5:
                        points = [20 if x == 1 else 10 if x == 0 else 0 for x in seq]
                    else:
                        points = [100/7 if x == 1 else 100/14 if x == 0 else 0 for x in seq]
                    perc = int(sum(points))
                    # Convert FTR to W/L/D
                    ftr_map = {1: 'W', 2: 'L', 0: 'D'}
                    seq_str = [ftr_map.get(x, '-') for x in seq]
                    return {'FTR_seq': seq_str, 'perc': perc}
                home_last5 = last_games_info(home_games, home_idx, 5)
                home_last7 = last_games_info(home_games, home_idx, 7)
                away_last5 = last_games_info(away_games, away_idx, 5)
                away_last7 = last_games_info(away_games, away_idx, 7)
                matches.append({
                    'home': home,
                    'away': away,
                    'FTR': match['FTR'],
                    'home_prev': home_prev,
                    'away_prev': away_prev,
                    'home_last5': home_last5,
                    'home_last7': home_last7,
                    'away_last5': away_last5,
                    'away_last7': away_last7
                })
            result.append({'matchday': int(md), 'matches': matches, 'game_frequency': game_frequency})
        return jsonify({'matchdays': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_ftr_variations')
def get_ftr_variations():
    league = request.args.get('league')
    season = request.args.get('season')
    if not league or not season:
        return jsonify({'error': 'Missing league or season'}), 400
    csv_path = os.path.join(DATA_FOLDER, league)
    if not os.path.exists(csv_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        df = pd.read_csv(csv_path)
        if 'Season' not in df.columns or 'MD' not in df.columns or 'FTR' not in df.columns:
            return jsonify({'error': 'Required columns missing'}), 400
        df = df[df['Season'] == season].copy()
        matchdays = sorted(df['MD'].dropna().unique(), key=lambda x: int(x))
        variation_counts = {}
        for md in matchdays:
            sub = df[df['MD'] == md]
            home = int((sub['FTR'] == 1).sum())
            away = int((sub['FTR'] == 2).sum())
            draw = int((sub['FTR'] == 0).sum())
            vec = sorted([home, away, draw], reverse=True)
            key = '-'.join(str(x) for x in vec)
            variation_counts[key] = variation_counts.get(key, 0) + 1
        # Sort by frequency descending, then by vector
        variations = sorted(variation_counts.items(), key=lambda x: (-x[1], x[0]), reverse=False)
        return jsonify({'variations': variations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
