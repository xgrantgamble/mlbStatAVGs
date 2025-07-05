# utils.py
"""
Helper functions for data processing, calculations, and team data construction.
"""
import logging
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import json # Import json for pretty printing

from mlb_api import MLBStatsAPI, MLB_API_BASE

logger = logging.getLogger(__name__)

TEAM_ABBREVIATIONS = {
    'Arizona Diamondbacks': 'ARI', 'Athletics': 'OAK', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS', 'Chicago White Sox': 'CWS', 'Chicago Cubs': 'CHC',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Yankees': 'NYY',
    'New York Mets': 'NYM', 'Oakland Athletics': 'OAK', 'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
    'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH'
}

# (All other functions remain the same as the previous version)
def get_team_logo_url(team_id: int) -> str:
    """Generates the URL for a team's logo."""
    if not team_id:
        return ""
    return f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{team_id}.svg"

def format_game_time(game_time_utc: str) -> str:
    """Formats a UTC game time string to Pacific Time."""
    if not game_time_utc:
        return "TBD"
    try:
        if game_time_utc.endswith('Z'):
            game_time_utc = game_time_utc[:-1] + "+00:00"
        utc_dt = datetime.fromisoformat(game_time_utc)
        pacific = pytz.timezone('US/Pacific')
        pacific_dt = utc_dt.astimezone(pacific)
        
        formatted_time = pacific_dt.strftime('%I:%M %p PT')
        if formatted_time.startswith('0'):
            return formatted_time[1:]
        return formatted_time
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse game time: {game_time_utc}. Error: {e}")
        return "TBD"

def get_stat_class(value: Any, stat: str) -> str:
    """Determines the CSS class for a stat based on its value."""
    try:
        val = float(value)
    except (ValueError, TypeError, AttributeError):
        return ""

    if val == 0:
        return ""

    thresholds = {
        'avg': {'good': 0.265, 'bad': 0.240},
        'slg': {'good': 0.450, 'bad': 0.380},
        'obp': {'good': 0.340, 'bad': 0.300},
        'era': {'good': 3.00, 'bad': 5.00, 'reverse': True},
        'whip': {'good': 1.20, 'bad': 1.40, 'reverse': True},
    }

    t = thresholds.get(stat)
    if not t:
        return ""

    if t.get('reverse', False):
        if val < t['good']: return 'stat-good'
        if val > t['bad']: return 'stat-bad'
    else:
        if val > t['good']: return 'stat-good'
        if val < t['bad']: return 'stat-bad'
    return ""

def _get_default_stats(stat_type: str) -> Dict[str, Any]:
    if stat_type == 'hitting':
        # Add 'k' for strikeouts to the default hitting stats
        return {'avg': '.000', 'obp': '.000', 'slg': '.000', 'hr': 0, 'rbi': 0, 'h': 0, 'ab': 0, 'k': 0}
    return {'era': '0.00', 'whip': '0.00', 'k': 0, 'bb': 0, 'ip': '0.0', 'h': 0, 'r': 0, 'gs': 0, 'sv': 0}

def _aggregate_hitting_stats(game_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not game_logs: return _get_default_stats('hitting')
    # Add 'k' for strikeouts to the totals dictionary
    totals = {'ab': 0, 'h': 0, 'hr': 0, 'rbi': 0, 'bb': 0, 'tb': 0, 'k': 0}
    for game in game_logs:
        stat = game.get('stat', {})
        totals['ab'] += stat.get('atBats', 0)
        totals['h'] += stat.get('hits', 0)
        totals['hr'] += stat.get('homeRuns', 0)
        totals['rbi'] += stat.get('rbi', 0)
        totals['bb'] += stat.get('baseOnBalls', 0)
        totals['tb'] += stat.get('totalBases', 0)
        # Aggregate strikeouts from the game log
        totals['k'] += stat.get('strikeOuts', 0)
        
    avg = f"{(totals['h'] / totals['ab']):.3f}" if totals['ab'] > 0 else ".000"
    obp = f"{((totals['h'] + totals['bb']) / (totals['ab'] + totals['bb'])):.3f}" if (totals['ab'] + totals['bb']) > 0 else ".000"
    slg = f"{(totals['tb'] / totals['ab']):.3f}" if totals['ab'] > 0 else ".000"
    
    # Add 'k' to the returned dictionary
    return {
        'avg': avg, 'obp': obp, 'slg': slg, 
        'hr': totals['hr'], 'rbi': totals['rbi'], 
        'h': totals['h'], 'ab': totals['ab'],
        'bb': totals['bb'], 'tb': totals['tb'], 'k': totals['k']
    }

def _aggregate_pitching_stats(game_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not game_logs: return _get_default_stats('pitching')
    totals = {'er': 0, 'h': 0, 'r': 0, 'bb': 0, 'k': 0, 'sv': 0, 'gs': 0}
    total_ip = 0.0
    for game in game_logs:
        stat = game.get('stat', {})
        ip_str = str(stat.get('inningsPitched', '0'))
        if '.' in ip_str:
            parts = ip_str.split('.')
            total_ip += int(parts[0]) + (int(parts[1]) / 3.0)
        else:
            total_ip += float(ip_str)
        totals['er'] += stat.get('earnedRuns', 0)
        totals['h'] += stat.get('hits', 0)
        totals['r'] += stat.get('runs', 0)
        totals['bb'] += stat.get('baseOnBalls', 0)
        totals['k'] += stat.get('strikeOuts', 0)
        totals['sv'] += stat.get('saves', 0)
        totals['gs'] += stat.get('gamesStarted', 0)
    era = f"{(totals['er'] * 9 / total_ip):.2f}" if total_ip > 0 else "0.00"
    whip = f"{((totals['bb'] + totals['h']) / total_ip):.2f}" if total_ip > 0 else "0.00"
    return {'era': era, 'whip': whip, 'k': totals['k'], 'bb': totals['bb'], 'ip': f"{total_ip:.1f}", 'h': totals['h'], 'r': totals['r'], 'gs': totals['gs'], 'sv': totals['sv']}

def get_player_stats_for_periods(player_id: int, stat_type: str, periods: Dict[str, int]) -> Dict[str, Any]:
    current_season = datetime.now().year
    game_logs = MLBStatsAPI.get_player_game_logs(player_id, stat_type, season=current_season)
    stats_by_period = {}
    if stat_type == 'hitting':
        played_games = [g for g in game_logs if g.get('stat', {}).get('atBats', 0) > 0]
        for period_name, num_games in periods.items():
            stats_by_period[period_name] = _aggregate_hitting_stats(played_games[:num_games])
    else: # pitching
        pitched_games = [g for g in game_logs if float(str(g.get('stat', {}).get('inningsPitched', '0'))) > 0]
        for period_name, num_starts in periods.items():
            stats_by_period[period_name] = _aggregate_pitching_stats(pitched_games[:num_starts])
    return stats_by_period

def process_team_roster_in_parallel(roster: List[Dict], stat_type: str, periods: Dict[str, int], max_workers: int = 10) -> List[Dict]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_player = {
            executor.submit(get_player_stats_for_periods, player['id'], stat_type, periods): player
            for player in roster
        }
        for future, player in future_to_player.items():
            try:
                player['stats_by_period'] = future.result()
            except Exception as e:
                logger.error(f"Error processing player {player['id']} for all periods: {e}")
                player['stats_by_period'] = {p: _get_default_stats(stat_type) for p in periods}
    return roster

def calculate_rolling_team_stats(batters: List[Dict], pitchers: List[Dict], period: str, games_played: int) -> Dict[str, Any]:
    if not batters: return {'AVG': '.000', 'OBP': '.000', 'SLG': '.000', 'HR': 0, 'AVG_HITS': '0.0', 'AVG_K': '0.0'}
    b_totals = {'ab': 0, 'h': 0, 'bb': 0, 'tb': 0, 'hr': 0}
    for batter in batters:
        stats = batter.get('stats_by_period', {}).get(period, {})
        if stats and stats.get('ab', 0) > 0:
            b_totals['ab'] += stats.get('ab', 0)
            b_totals['h'] += stats.get('h', 0)
            b_totals['bb'] += stats.get('bb', 0)
            b_totals['hr'] += stats.get('hr', 0)
            b_totals['tb'] += stats.get('tb', 0)
    p_totals = {'k': 0}
    for pitcher in pitchers:
        stats = pitcher.get('stats_by_period', {}).get(period, {})
        if stats and float(stats.get('ip', '0.0')) > 0:
            p_totals['k'] += stats.get('k', 0)
    team_avg = f"{(b_totals['h'] / b_totals['ab']):.3f}" if b_totals['ab'] > 0 else ".000"
    team_obp = f"{((b_totals['h'] + b_totals['bb']) / (b_totals['ab'] + b_totals['bb'])):.3f}" if (b_totals['ab'] + b_totals['bb']) > 0 else ".000"
    team_slg = f"{(b_totals['tb'] / b_totals['ab']):.3f}" if b_totals['ab'] > 0 else ".000"
    avg_hits = f"{(b_totals['h'] / games_played):.1f}" if games_played > 0 else "0.0"
    avg_k = f"{(p_totals['k'] / games_played):.1f}" if games_played > 0 else "0.0"
    return {'AVG': team_avg, 'OBP': team_obp, 'SLG': team_slg, 'HR': b_totals['hr'], 'AVG_HITS': avg_hits, 'AVG_K': avg_k}


def get_team_game_history(team_id: int, days: int) -> Dict[str, Any]:
    """
    Fetches a team's recent game history and calculates their win-loss record.
    """
    pacific = pytz.timezone('US/Pacific')
    end_date = datetime.now(pacific)
    start_date = end_date - timedelta(days=days)

    url = f"{MLB_API_BASE}/schedule"
    params = {
        'sportId': 1,
        'teamId': team_id,
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d'),
        'hydrate': 'decisions,team,linescore',
    }
    try:
        data = MLBStatsAPI._make_api_request(url, params)
        wins = 0
        losses = 0
        game_log = []
        
        all_games = [game for date_entry in data.get('dates', []) for game in date_entry.get('games', [])]

        final_games = [
            g for g in all_games 
            if g.get('status', {}).get('abstractGameState') == 'Final'
        ]
        
        final_games.sort(key=lambda g: g.get('gameDate', ''), reverse=True)

        for game in final_games:
            try:
                game_date_str = game.get('gameDate')
                if not game_date_str:
                    continue

                away_team = game['teams']['away']
                home_team = game['teams']['home']
                is_our_team_away = away_team['team']['id'] == team_id
                
                our_score = away_team.get('score', 0) if is_our_team_away else home_team.get('score', 0)
                opp_score = home_team.get('score', 0) if is_our_team_away else away_team.get('score', 0)
                opponent_name = home_team.get('team', {}).get('name') if is_our_team_away else away_team.get('team', {}).get('name')

                opponent_abbr = TEAM_ABBREVIATIONS.get(opponent_name, '???')
                result = 'W' if our_score > opp_score else 'L'
                if result == 'W':
                    wins += 1
                else:
                    losses += 1
                
                game_date_utc = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                game_date_pacific = game_date_utc.astimezone(pacific)
                
                # FIX: Use a cross-platform compatible way to format the date.
                formatted_date = f"{game_date_pacific.month}/{game_date_pacific.day}"

                game_log.append({'result': result, 'date': formatted_date, 'opponent': opponent_abbr})

            except Exception as e_inner:
                logger.warning(f"Could not process game data for game pk {game.get('gamePk')}. Error: {e_inner}")
                continue

        return {'record': f"{wins}-{losses}", 'games_played': len(final_games), 'game_log': game_log}

    except Exception as e:
        logger.error(f"Error fetching game history for team {team_id}: {e}", exc_info=True)
        return {'record': '0-0', 'games_played': 0, 'game_log': []}