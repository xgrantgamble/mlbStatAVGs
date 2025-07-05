# routes.py

"""
Flask routes for the MLB Stats Tracker application.
"""

import logging
from datetime import datetime
import pytz
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from typing import Dict, Any

from mlb_api import MLBStatsAPI
from utils import (
    TEAM_ABBREVIATIONS, get_team_logo_url, format_game_time,
    process_team_roster_in_parallel, calculate_rolling_team_stats, get_team_game_history
)
from extensions import cache

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Renders the home page with today's games."""
    pacific_tz = pytz.timezone('US/Pacific')
    today_str = datetime.now(pacific_tz).strftime('%Y-%m-%d')
    
    games_data = MLBStatsAPI.get_todays_games(today_str)
    
    games = []
    for game in games_data:
        home_team_info = game.get('teams', {}).get('home', {}).get('team', {})
        away_team_info = game.get('teams', {}).get('away', {}).get('team', {})
        
        home_team_name = home_team_info.get('name', 'N/A')
        away_team_name = away_team_info.get('name', 'N/A')
        
        games.append({
            'home_id': home_team_info.get('id'),
            'away_id': away_team_info.get('id'),
            'home_team': home_team_name,
            'away_team': away_team_name,
            'home_abbr': TEAM_ABBREVIATIONS.get(home_team_name, ''),
            'away_abbr': TEAM_ABBREVIATIONS.get(away_team_name, ''),
            'home_logo': get_team_logo_url(home_team_info.get('id')),
            'away_logo': get_team_logo_url(away_team_info.get('id')),
            'formatted_time': format_game_time(game.get('gameDate')),
            'status': 'postponed' if 'postponed' in game.get('status', {}).get('detailedState', '').lower() else 'scheduled'
        })

    favorites = session.get('favorites', [])
    current_date = datetime.now(pacific_tz).strftime('%A, %B %d, %Y')
    
    return render_template('home.html', games=games, favorites=favorites, current_date=current_date)

@main_bp.route('/details/<int:home_id>/<int:away_id>')
def game_details(home_id: int, away_id: int):
    """Renders the details page for a specific game."""
    try:
        home_team_data = MLBStatsAPI.get_team_info(home_id)
        away_team_data = MLBStatsAPI.get_team_info(away_id)

        if not home_team_data or not away_team_data or 'teams' not in home_team_data or not home_team_data['teams']:
            logger.error(f"Could not retrieve team info for home_id={home_id} or away_id={away_id}")
            return redirect(url_for('main.home'))

        home_team_info = home_team_data['teams'][0]
        away_team_info = away_team_data['teams'][0]

        home_roster = MLBStatsAPI.get_team_roster(home_id)
        away_roster = MLBStatsAPI.get_team_roster(away_id)
        
        hitter_periods = {'7': 7, '10': 10, '21': 21}
        pitcher_periods = {'7': 2, '10': 3, '21': 4}

        home_batters = process_team_roster_in_parallel(home_roster['batters'][:15], 'hitting', hitter_periods)
        away_batters = process_team_roster_in_parallel(away_roster['batters'][:15], 'hitting', hitter_periods)
        home_pitchers = process_team_roster_in_parallel(home_roster['pitchers'][:15], 'pitching', pitcher_periods)
        away_pitchers = process_team_roster_in_parallel(away_roster['pitchers'][:15], 'pitching', pitcher_periods)

        home_team = {'id': home_id, 'name': home_team_info.get('name'), 'fullRoster': {'batters': {}, 'pitchers': {}}, 'rollingTeamStats': {}, 'gameHistory': {}}
        away_team = {'id': away_id, 'name': away_team_info.get('name'), 'fullRoster': {'batters': {}, 'pitchers': {}}, 'rollingTeamStats': {}, 'gameHistory': {}}

        for period in ['7', '10', '21']:
            # Sort batters by At-Bats (ab) for the current period
            home_team['fullRoster']['batters'][period] = sorted(home_batters, key=lambda p: p['stats_by_period'][period].get('ab', 0), reverse=True)
            away_team['fullRoster']['batters'][period] = sorted(away_batters, key=lambda p: p['stats_by_period'][period].get('ab', 0), reverse=True)
            
            # Sort pitchers by Games Started (gs) for the current period
            home_team['fullRoster']['pitchers'][period] = sorted(home_pitchers, key=lambda p: p['stats_by_period'][period].get('gs', 0), reverse=True)
            away_team['fullRoster']['pitchers'][period] = sorted(away_pitchers, key=lambda p: p['stats_by_period'][period].get('gs', 0), reverse=True)

            # Get game history and calculate rolling team stats
            home_history = get_team_game_history(home_id, int(period))
            away_history = get_team_game_history(away_id, int(period))
            home_team['gameHistory'][period] = home_history
            away_team['gameHistory'][period] = away_history
            home_team['rollingTeamStats'][period] = calculate_rolling_team_stats(home_batters, home_pitchers, period, home_history['games_played'])
            away_team['rollingTeamStats'][period] = calculate_rolling_team_stats(away_batters, away_pitchers, period, away_history['games_played'])

        favorites = session.get('favorites', [])

        return render_template('details.html', home_team=home_team, away_team=away_team, favorites=favorites)
    except Exception as e:
        logger.error(f"Error in game_details for {home_id} vs {away_id}: {e}", exc_info=True)
        return redirect(url_for('main.home'))

@main_bp.route('/api/load-stats/<int:home_id>/<int:away_id>/<int:days>')
def load_stats_api(home_id: int, away_id: int, days: int):
    return jsonify({"message": "This API endpoint is no longer used by the primary UI.", "status": "success"})

@main_bp.route('/favorites', methods=['POST'])
def toggle_favorite():
    team_name = request.form.get('favorite')
    if team_name:
        favorites = session.get('favorites', [])
        if team_name in favorites:
            favorites.remove(team_name)
        else:
            favorites.append(team_name)
        session['favorites'] = favorites
    return redirect(request.referrer or url_for('main.home'))

@main_bp.route('/reset_favorites', methods=['POST'])
def reset_favorites():
    session['favorites'] = []
    return redirect(url_for('main.home'))

@main_bp.route('/admin/clear-cache')
def clear_cache():
    cache.clear()
    return "Cache has been cleared!"