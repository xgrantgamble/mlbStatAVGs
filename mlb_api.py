# mlb_api.py

"""
Module for interacting with the MLB Stats API.

This module contains the MLBStatsAPI class which handles all API requests,
data fetching, parsing, and includes a rate limiter to avoid being blocked.
"""
import requests
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from extensions import cache

# Configure logging
logger = logging.getLogger(__name__)

# MLB Stats API base URL
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


class RateLimiter:
    """A simple thread-safe rate limiter. Prevents exceeding the API call limit."""
    def __init__(self, max_calls: int = 100, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Blocks until a call can be made, if necessary."""
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.time_window]
            if len(self.calls) >= self.max_calls:
                wait_duration = self.time_window - (now - self.calls[0])
                logger.warning(f"Rate limit reached. Waiting for {wait_duration:.2f} seconds.")
                if wait_duration > 0:
                    time.sleep(wait_duration)
            self.calls.append(time.time())


rate_limiter = RateLimiter(max_calls=100, time_window=60)


class MLBStatsAPI:
    """
    A wrapper for the MLB Stats API with caching, rate limiting, and error handling.
    """

    @staticmethod
    def _make_api_request(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Dict[str, Any]:
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
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out for URL: {url}. Error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for URL: {url}. Error: {e}")
            raise

    @staticmethod
    def get_todays_games(date_str: str) -> List[Dict[str, Any]]:
        cache_key = f"games_{date_str}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        logger.info(f"Fetching games for date: {date_str}")
        url = f"{MLB_API_BASE}/schedule"
        params = {'sportId': 1, 'date': date_str, 'hydrate': 'team'}
        try:
            data = MLBStatsAPI._make_api_request(url, params)
            games = []
            if 'dates' in data and data['dates']:
                games = data['dates'][0].get('games', [])
            
            cache.set(cache_key, games, timeout=86400)
            return games
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    def get_team_roster(team_id: int) -> Dict[str, List[Dict[str, Any]]]:
        cache_key = f"roster_{team_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

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
            
            cache.set(cache_key, roster, timeout=86400)
            return roster
        except requests.exceptions.RequestException:
            return roster

    @staticmethod
    def get_player_game_logs(player_id: int, stat_group: str, season: int = 2026) -> List[Dict[str, Any]]:
        if season is None:
            season = datetime.now().year
            
        cache_key = f"logs_{player_id}_{stat_group}_{season}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        logger.info(f"Fetching {season} game logs for player {player_id} ({stat_group})")
        url = f"{MLB_API_BASE}/people/{player_id}/stats"
        params = {'stats': 'gameLog', 'group': stat_group, 'season': season}
        try:
            data = MLBStatsAPI._make_api_request(url, params)
            games = []
            if data.get('stats') and data['stats'][0].get('splits'):
                games = data['stats'][0]['splits']
                games.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            cache.set(cache_key, games, timeout=86400)
            return games
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    def get_team_info(team_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"info_{team_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        logger.info(f"Fetching info for team ID: {team_id}")
        url = f"{MLB_API_BASE}/teams/{team_id}"
        try:
            data = MLBStatsAPI._make_api_request(url, {'sportId': 1})
            cache.set(cache_key, data, timeout=86400)
            return data
        except requests.exceptions.RequestException:
            return None