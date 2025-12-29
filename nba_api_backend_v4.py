"""
NBA Advanced Analytics API v4.0
================================
Dean Oliver's Four Factors + Pythagorean Expectation

Kurulum:
    pip install flask flask-cors nba_api pandas

Çalıştırma:
    python nba_api_backend_v4.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import time
import math

from nba_api.stats.endpoints import (
    scoreboardv2,
    teamgamelog,
    leaguedashteamstats
)
from nba_api.stats.static import teams

app = Flask(__name__)
CORS(app)

API_DELAY = 0.6

def get_current_season():
    now = datetime.now()
    year = now.year
    month = now.month
    if month >= 10:
        season_start = year
    else:
        season_start = year - 1
    season_end = season_start + 1
    return f"{season_start}-{str(season_end)[-2:]}"

def get_season_info():
    season = get_current_season()
    now = datetime.now()
    season_start_year = int(season.split('-')[0])
    return {
        'current_season': season,
        'season_start': f"Ekim {season_start_year}",
        'season_end': f"Haziran {season_start_year + 1}",
        'analytics_version': 'Advanced v4.0 - Four Factors + Pythagorean'
    }

CURRENT_SEASON = get_current_season()
print(f"🏀 Aktif Sezon: {CURRENT_SEASON}")

# Cache
_advanced_stats_cache = {}
_cache_timestamp = None
CACHE_DURATION = 300

def get_cached_advanced_stats():
    global _advanced_stats_cache, _cache_timestamp
    now = datetime.now()
    
    if _cache_timestamp and (now - _cache_timestamp).seconds < CACHE_DURATION and _advanced_stats_cache:
        print("📦 Cache'den yükleniyor...")
        return _advanced_stats_cache
    
    print("🔄 API'den yeni veri çekiliyor...")
    
    try:
        time.sleep(API_DELAY)
        league_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense='Advanced',
            per_mode_detailed='PerGame'
        )
        df = league_stats.get_data_frames()[0]
        
        if df.empty:
            return {}
        
        stats_dict = {}
        for _, row in df.iterrows():
            team_id = row['TEAM_ID']
            stats_dict[team_id] = {
                'team_id': team_id,
                'team_name': row['TEAM_NAME'],
                'games_played': int(row['GP']),
                'wins': int(row['W']),
                'losses': int(row['L']),
                'win_pct': float(row['W_PCT']),
                'off_rating': float(row.get('OFF_RATING', 110)),
                'def_rating': float(row.get('DEF_RATING', 110)),
                'net_rating': float(row.get('NET_RATING', 0)),
                'pace': float(row.get('PACE', 100)),
                'efg_pct': float(row.get('EFG_PCT', 0.5)),
                'tov_pct': float(row.get('TM_TOV_PCT', 0.12)),
                'oreb_pct': float(row.get('OREB_PCT', 0.25)),
                'fta_rate': float(row.get('FTA_RATE', 0.25)),
                'opp_efg_pct': float(row.get('OPP_EFG_PCT', 0.5)),
                'opp_tov_pct': float(row.get('OPP_TOV_PCT', 0.12)),
                'opp_oreb_pct': float(row.get('OPP_OREB_PCT', 0.25)),
                'opp_fta_rate': float(row.get('OPP_FTA_RATE', 0.25)),
                'pts': float(row.get('PTS', 110)),
            }
        
        _advanced_stats_cache = stats_dict
        _cache_timestamp = now
        print(f"✅ {len(stats_dict)} takım yüklendi")
        return stats_dict
        
    except Exception as e:
        print(f"❌ Advanced stats hatası: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_team_info(team_id):
    all_teams = teams.get_teams()
    return next((t for t in all_teams if t['id'] == team_id), None)

def get_team_by_abbreviation(abbr):
    all_teams = teams.get_teams()
    return next((t for t in all_teams if t['abbreviation'] == abbr.upper()), None)

def get_team_last_n_games(team_id, n=5, season=None):
    if season is None:
        season = CURRENT_SEASON
    try:
        time.sleep(API_DELAY)
        game_log = teamgamelog.TeamGameLog(team_id=team_id, season=season)
        df = game_log.get_data_frames()[0]
        if df.empty:
            return []
        results = []
        for _, game in df.head(n).iterrows():
            results.append({
                'date': game['GAME_DATE'],
                'matchup': game['MATCHUP'],
                'result': 'W' if game['WL'] == 'W' else 'L',
                'points': int(game['PTS'])
            })
        return results
    except Exception as e:
        print(f"Error getting team games: {e}")
        return []

def calculate_pythagorean_expectation(pts_scored, pts_allowed, exponent=13.91):
    if pts_scored <= 0 or pts_allowed <= 0:
        return 0.5
    pts_exp = math.pow(pts_scored, exponent)
    opp_exp = math.pow(pts_allowed, exponent)
    return pts_exp / (pts_exp + opp_exp)

def calculate_four_factors_score(team_stats, is_offense=True):
    if is_offense:
        efg = team_stats['efg_pct']
        tov = 1 - team_stats['tov_pct']
        orb = team_stats['oreb_pct']
        ftr = min(team_stats['fta_rate'], 0.4) / 0.4
    else:
        efg = 1 - team_stats['opp_efg_pct']
        tov = team_stats['opp_tov_pct']
        orb = 1 - team_stats['opp_oreb_pct']
        ftr = 1 - min(team_stats['opp_fta_rate'], 0.4) / 0.4
    return 0.40 * efg + 0.25 * tov + 0.20 * orb + 0.15 * ftr

def calculate_expected_total_score(home_stats, away_stats):
    avg_pace = (home_stats['pace'] + away_stats['pace']) / 2
    home_exp = avg_pace * (home_stats['off_rating'] / 100)
    away_exp = avg_pace * (away_stats['off_rating'] / 100)
    league_avg_def = 114
    home_adj = home_exp * (away_stats['def_rating'] / league_avg_def)
    away_adj = away_exp * (home_stats['def_rating'] / league_avg_def)
    return {
        'total': round(home_adj + away_adj, 1),
        'home_expected': round(home_adj, 1),
        'away_expected': round(away_adj, 1),
        'pace': round(avg_pace, 1)
    }

def get_confidence_level(prob):
    if prob >= 68:
        return {'level': 'very_high', 'label': 'Çok Yüksek', 'emoji': '🔥🔥'}
    elif prob >= 62:
        return {'level': 'high', 'label': 'Yüksek', 'emoji': '🔥'}
    elif prob >= 55:
        return {'level': 'medium', 'label': 'Orta', 'emoji': '⚡'}
    return {'level': 'low', 'label': 'Düşük', 'emoji': '❓'}

def calculate_advanced_win_probability(home_stats, away_stats, home_last5, away_last5):
    # Pythagorean
    home_opp_pts = home_stats['pts'] * (home_stats['def_rating'] / home_stats['off_rating'])
    away_opp_pts = away_stats['pts'] * (away_stats['def_rating'] / away_stats['off_rating'])
    
    home_pyth = calculate_pythagorean_expectation(home_stats['pts'], home_opp_pts)
    away_pyth = calculate_pythagorean_expectation(away_stats['pts'], away_opp_pts)
    
    home_pyth_net = max(0, min(1, home_stats['net_rating'] / 28 + 0.5))
    away_pyth_net = max(0, min(1, away_stats['net_rating'] / 28 + 0.5))
    
    home_pyth = (home_pyth + home_pyth_net) / 2
    away_pyth = (away_pyth + away_pyth_net) / 2
    
    # Four Factors
    home_ff = (calculate_four_factors_score(home_stats, True) + calculate_four_factors_score(home_stats, False)) / 2
    away_ff = (calculate_four_factors_score(away_stats, True) + calculate_four_factors_score(away_stats, False)) / 2
    
    # Form
    home_form = sum(1 for r in home_last5 if r['result'] == 'W') / 5 if home_last5 else 0.5
    away_form = sum(1 for r in away_last5 if r['result'] == 'W') / 5 if away_last5 else 0.5
    
    # Home advantage
    home_adv = 0.58
    
    # Weighted score
    home_score = 0.40 * home_pyth + 0.30 * home_ff + 0.15 * home_form + 0.15 * home_adv
    away_score = 0.40 * away_pyth + 0.30 * away_ff + 0.15 * away_form + 0.15 * (1 - home_adv)
    
    total = home_score + away_score
    home_prob = round((home_score / total) * 100)
    away_prob = 100 - home_prob
    
    expected = calculate_expected_total_score(home_stats, away_stats)
    
    return {
        'home_probability': home_prob,
        'away_probability': away_prob,
        'predicted_winner': 'home' if home_prob > away_prob else 'away',
        'confidence': get_confidence_level(max(home_prob, away_prob)),
        'expected_total': expected,
        'advanced_metrics': {
            'home': {
                'pythagorean': round(home_pyth * 100, 1),
                'four_factors': round(home_ff * 100, 1),
                'off_rating': round(home_stats['off_rating'], 1),
                'def_rating': round(home_stats['def_rating'], 1),
                'net_rating': round(home_stats['net_rating'], 1),
                'pace': round(home_stats['pace'], 1),
                'efg_pct': round(home_stats['efg_pct'] * 100, 1),
                'tov_pct': round(home_stats['tov_pct'] * 100, 1),
                'oreb_pct': round(home_stats['oreb_pct'] * 100, 1),
                'fta_rate': round(home_stats['fta_rate'] * 100, 1)
            },
            'away': {
                'pythagorean': round(away_pyth * 100, 1),
                'four_factors': round(away_ff * 100, 1),
                'off_rating': round(away_stats['off_rating'], 1),
                'def_rating': round(away_stats['def_rating'], 1),
                'net_rating': round(away_stats['net_rating'], 1),
                'pace': round(away_stats['pace'], 1),
                'efg_pct': round(away_stats['efg_pct'] * 100, 1),
                'tov_pct': round(away_stats['tov_pct'] * 100, 1),
                'oreb_pct': round(away_stats['oreb_pct'] * 100, 1),
                'fta_rate': round(away_stats['fta_rate'] * 100, 1)
            }
        },
        'model_weights': {'pythagorean': '40%', 'four_factors': '30%', 'recent_form': '15%', 'home_advantage': '15%'}
    }

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        'name': '🏀 NBA Advanced Analytics API',
        'version': '4.0',
        'season': get_season_info(),
        'model': {'pythagorean': '40%', 'four_factors': '30%', 'form': '15%', 'home_adv': '15%'},
        'endpoints': {
            'GET /api/advanced/<home>/<away>': 'Gelişmiş tahmin',
            'GET /api/games/today': 'Bugünün maçları',
            'GET /api/teams': 'Tüm takımlar'
        }
    })

@app.route('/api/season')
def get_season():
    return jsonify(get_season_info())

@app.route('/api/teams')
def get_all_teams():
    all_teams = teams.get_teams()
    return jsonify({'count': len(all_teams), 'teams': sorted(all_teams, key=lambda x: x['full_name'])})

@app.route('/api/quick/<home_abbr>/<away_abbr>')
@app.route('/api/advanced/<home_abbr>/<away_abbr>')
def advanced_predict(home_abbr, away_abbr):
    try:
        home_team = get_team_by_abbreviation(home_abbr)
        away_team = get_team_by_abbreviation(away_abbr)
        
        if not home_team:
            return jsonify({'error': f"'{home_abbr}' bulunamadı"}), 404
        if not away_team:
            return jsonify({'error': f"'{away_abbr}' bulunamadı"}), 404
        
        print(f"\n🏀 Advanced: {home_team['full_name']} vs {away_team['full_name']}")
        
        all_stats = get_cached_advanced_stats()
        if not all_stats:
            return jsonify({'error': 'Advanced stats alınamadı'}), 500
        
        home_stats = all_stats.get(home_team['id'])
        away_stats = all_stats.get(away_team['id'])
        
        if not home_stats or not away_stats:
            return jsonify({'error': 'Takım stats bulunamadı'}), 500
        
        home_last5 = get_team_last_n_games(home_team['id'], 5)
        away_last5 = get_team_last_n_games(away_team['id'], 5)
        
        pred = calculate_advanced_win_probability(home_stats, away_stats, home_last5, away_last5)
        
        winner = home_team if pred['predicted_winner'] == 'home' else away_team
        winner_prob = pred['home_probability'] if pred['predicted_winner'] == 'home' else pred['away_probability']
        
        return jsonify({
            'season': CURRENT_SEASON,
            'matchup': f"{home_team['abbreviation']} vs {away_team['abbreviation']}",
            'venue': f"{home_team['full_name']} (Ev Sahibi)",
            'home_team': {
                'name': home_team['full_name'],
                'abbreviation': home_team['abbreviation'],
                'record': f"{home_stats['wins']}-{home_stats['losses']}",
                'win_pct': round(home_stats['win_pct'] * 100, 1),
                'last_5': [g['result'] for g in home_last5],
                'win_probability': pred['home_probability'],
                'advanced': pred['advanced_metrics']['home']
            },
            'away_team': {
                'name': away_team['full_name'],
                'abbreviation': away_team['abbreviation'],
                'record': f"{away_stats['wins']}-{away_stats['losses']}",
                'win_pct': round(away_stats['win_pct'] * 100, 1),
                'last_5': [g['result'] for g in away_last5],
                'win_probability': pred['away_probability'],
                'advanced': pred['advanced_metrics']['away']
            },
            'prediction': {
                'winner': winner['full_name'],
                'winner_abbr': winner['abbreviation'],
                'probability': winner_prob,
                'confidence': pred['confidence'],
                'model_weights': pred['model_weights']
            },
            'over_under': {
                'projected_total': pred['expected_total']['total'],
                'home_projected': pred['expected_total']['home_expected'],
                'away_projected': pred['expected_total']['away_expected'],
                'game_pace': pred['expected_total']['pace']
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/games/today')
def get_todays_games():
    try:
        time.sleep(API_DELAY)
        board = scoreboardv2.ScoreboardV2()
        games_header = board.game_header.get_data_frame()
        
        if games_header.empty:
            return jsonify({'date': datetime.now().strftime('%Y-%m-%d'), 'message': 'Bugün maç yok', 'games_count': 0, 'games': []})
        
        all_stats = get_cached_advanced_stats()
        games = []
        
        for _, game in games_header.iterrows():
            home_id, away_id = game['HOME_TEAM_ID'], game['VISITOR_TEAM_ID']
            home_info, away_info = get_team_info(home_id), get_team_info(away_id)
            home_stats, away_stats = all_stats.get(home_id), all_stats.get(away_id)
            
            if not home_stats or not away_stats:
                continue
            
            home_last5 = get_team_last_n_games(home_id, 5)
            away_last5 = get_team_last_n_games(away_id, 5)
            pred = calculate_advanced_win_probability(home_stats, away_stats, home_last5, away_last5)
            winner = home_info if pred['predicted_winner'] == 'home' else away_info
            
            games.append({
                'game_id': game['GAME_ID'],
                'status': game['GAME_STATUS_TEXT'],
                'home_team': {'name': home_info['full_name'], 'abbreviation': home_info['abbreviation'], 'record': f"{home_stats['wins']}-{home_stats['losses']}", 'off_rating': round(home_stats['off_rating'], 1), 'def_rating': round(home_stats['def_rating'], 1), 'pace': round(home_stats['pace'], 1), 'probability': pred['home_probability']},
                'away_team': {'name': away_info['full_name'], 'abbreviation': away_info['abbreviation'], 'record': f"{away_stats['wins']}-{away_stats['losses']}", 'off_rating': round(away_stats['off_rating'], 1), 'def_rating': round(away_stats['def_rating'], 1), 'pace': round(away_stats['pace'], 1), 'probability': pred['away_probability']},
                'prediction': {'winner': winner['full_name'], 'confidence': pred['confidence']},
                'expected_total': pred['expected_total']['total']
            })
        
        return jsonify({'season': CURRENT_SEASON, 'date': datetime.now().strftime('%Y-%m-%d'), 'games_count': len(games), 'games': games})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print()
    print("🏀 NBA Advanced Analytics API v4.0")
    print("=" * 55)
    print(f"📅 Aktif Sezon: {CURRENT_SEASON}")
    print()
    print("📊 Model: Pythagorean 40% | Four Factors 30% | Form 15% | Home 15%")
    print()
    print("📍 Endpoints:")
    print("   /api/advanced/<home>/<away>  → Gelişmiş tahmin")
    print("   /api/games/today             → Bugünün maçları")
    print()
    print("💡 Örnek: curl http://localhost:5000/api/advanced/LAL/BOS")
    print()
    print("=" * 55)
    print("🚀 Server: http://localhost:5000")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
