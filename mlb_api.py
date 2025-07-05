"""
Module for interacting with the MLB Stats API.

This module contains the MLBStatsAPI class which handles all API requests,
data fetching, parsing, and includes a rate limiter to avoid being blocked.
"""
import requests
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from extensions import cache # Import cache instance

# Configure logging
logger = logging.getLogger(__name__)

# MLB Stats API base URL
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

class RateLimiter:
    """A simple thread-safe rate limiter."""
    def __init__(self, max_calls: int = 80, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Blocks until a call can be made, if necessary."""
        with self.lock:
            now = time.time()
            # Remove calls that are outside the time window
            self.calls = [t for t in self.calls if now - t < self.time_window]
            if len(self.calls) >= self.max_calls:
                # Calculate wait time based on the oldest call
                wait_duration = self.time_window - (now - self.calls[0])
                logger.warning(f"Rate limit reached. Waiting for {wait_duration:.2f} seconds.")
                if wait_duration > 0:
                    time.sleep(wait_duration)
            self.calls.append(time.time())

rate_limiter = RateLimiter()

class MLBStatsAPI:
    """
    A wrapper for the MLB Stats API with caching, rate limiting, and error handling.
    """
    @staticmethod
    def _make_api_request(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Dict[str, Any]:
        """
        Makes a rate-limited GET request to the MLB API.

        Args:
            url: The API endpoint URL.
            params: A dictionary of query parameters.
            timeout: Request timeout in seconds.

        Returns:
            A dictionary containing the JSON response.
            
        Raises:
            requests.exceptions.RequestException: For network or HTTP errors.
        """
        rate_limiter.wait_if_needed()
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out for URL: {url}. Error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for URL: {url}. Error: {e}")
            raise

    @staticmethod
    @cache.memoize()
    def get_todays_games(date_str: str) -> List[Dict[str, Any]]:
        """
        Fetches all MLB games for a given date.

        Args:
            date_str: The date in 'YYYY-MM-DD' format.

        Returns:
            A list of dictionaries, each representing a game.
        """
        logger.info(f"Fetching games for date: {date_str}")
        url = f"{MLB_API_BASE}/schedule"
        params = {'sportId': 1, 'date': date_str, 'hydrate': 'team'}
        try:
            data = MLBStatsAPI._make_api_request(url, params)
            if 'dates' in data and data['dates']:
                return data['dates'][0].get('games', [])
            return []
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    @cache.memoize()
    def get_team_roster(team_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches the roster for a given team ID.

        Args:
            team_id: The MLB team ID.

        Returns:
            A dictionary with 'batters' and 'pitchers' lists.
        """
        logger.info(f"Fetching roster for team ID: {team_id}")
        url = f"{MLB_API_BASE}/teams/{team_id}/roster"
        params = {'rosterType': 'active'}
        roster = {'batters': [], 'pitchers': []}
        try:
            data = MLBStatsAPI._make_api_request(url, params)
            for player in data.get('roster', []):
                player_info = {
                    'id': player['person']['id'],
                    'name': player['person']['fullName'],
                    'position': player['position']['abbreviation'],
                }
                if player['position']['type'] == 'Pitcher':
                    roster['pitchers'].append(player_info)
                else:
                    roster['batters'].append(player_info)
            return roster
        except requests.exceptions.RequestException:
            return roster

    @staticmethod
    @cache.memoize()
    def get_player_game_logs(player_id: int, stat_group: str, season: int = None) -> List[Dict[str, Any]]:
        if season is None:
            season = datetime.now().year
        """
        Fetches all game logs for a player for a given season.

        Args:
            player_id: The MLB player ID.
            stat_group: 'hitting' or 'pitching'.
            season: The year of the season.

        Returns:
            A list of game log splits.
        """
        logger.info(f"Fetching {season} game logs for player {player_id} ({stat_group})")
        url = f"{MLB_API_BASE}/people/{player_id}/stats"
        params = {'stats': 'gameLog', 'group': stat_group, 'season': season}
        try:
            data = MLBStatsAPI._make_api_request(url, params)
            if data.get('stats') and data['stats'][0].get('splits'):
                # Sort by date descending to have the most recent games first
                games = data['stats'][0]['splits']
                games.sort(key=lambda x: x.get('date', ''), reverse=True)
                return games
            return []
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    @cache.memoize()
    def get_team_info(team_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches basic information for a team.

        Args:
            team_id: The MLB team ID.

        Returns:
            A dictionary with team info or None on error.
        """
        logger.info(f"Fetching info for team ID: {team_id}")
        url = f"{MLB_API_BASE}/teams/{team_id}"
        try:
            return MLBStatsAPI._make_api_request(url, {'sportId': 1})
        except requests.exceptions.RequestException:
            return None
