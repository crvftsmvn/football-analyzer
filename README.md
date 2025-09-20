# Football Data Analysis Flask Application

A Flask web application for analyzing football/soccer match data across different leagues and seasons.

## Features

- **Multi-League Support**: Analyze data from multiple football leagues including:
  - English Premier League
  - German Bundesliga
  - Italian Serie A
  - Spanish La Liga
  - Turkish Super League
  - Portuguese League

- **Season Analysis**: View data by specific seasons
- **Matchday Vectors**: Analyze matchday patterns and results
- **FTR Variations**: Study Full Time Result variations across matchdays
- **Detailed Match Information**: Get comprehensive match details including team performance history

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd neww
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Live Demo

🌐 **Try the application online:** [https://analyzer-5zun.onrender.com/](https://analyzer-5zun.onrender.com/)

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

- `GET /` - Main application interface
- `GET /get_seasons?league=<league_file>` - Get available seasons for a league
- `GET /get_matchday_vectors?league=<league_file>&season=<season>` - Get matchday data vectors
- `GET /get_matchday_details?league=<league_file>&season=<season>` - Get detailed matchday information
- `GET /get_ftr_variations?league=<league_file>&season=<season>` - Get FTR variations

## Data Format

The application expects CSV files in the `data/` directory with the following columns:
- `Season`: The season identifier
- `MD`: Matchday number
- `FTR`: Full Time Result (1=Home win, 0=Draw, 2=Away win)
- `Home`: Home team name
- `Away`: Away team name
- `hScre`: Half-time score
- `Date`: Match date (optional)

## Version History

- **v1.0** - Initial stable release with core functionality

## License

This project is for educational and analysis purposes.
