# tasks.py

"""
Background caching tasks for the app.
"""
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytz

from mlb_api import MLBStatsAPI
from extensions import cache
from utils import process_team_roster_in_parallel, get_team_game_history

logger = logging.getLogger(__name__)


def warm_single_game(app, game, index, total):
    """Warms cache for a single game. Designed to run in a thread."""
    with app.app_context():
        try:
            if 'postponed' in game.get('status', {}).get('detailedState', '').lower():
                logger.info(f"⏭️ Skipping postponed game {index}/{total}.")
                return

            home_id = game['teams']['home']['team']['id']
            away_id = game['teams']['away']['team']['id']
            away_name = game['teams']['away']['team']['name']
            home_name = game['teams']['home']['team']['name']
            logger.info(f"Warming game {index}/{total}: {away_name} @ {home_name}...")

            # --- PRE-LOAD TEAM INFO ---
            MLBStatsAPI.get_team_info(home_id)
            MLBStatsAPI.get_team_info(away_id)

            # --- PRE-LOAD GAME HISTORY ---
            for period in [7, 10, 21]:
                get_team_game_history(home_id, period)
                get_team_game_history(away_id, period)

            hitter_periods = {'7': 7, '10': 10, '21': 21}
            pitcher_periods = {'7': 2, '10': 3, '21': 4}

            home_roster = MLBStatsAPI.get_team_roster(home_id)
            away_roster = MLBStatsAPI.get_team_roster(away_id)

            if home_roster.get('batters'):
                process_team_roster_in_parallel(home_roster['batters'][:15], 'hitting', hitter_periods, max_workers=8)
            if home_roster.get('pitchers'):
                process_team_roster_in_parallel(home_roster['pitchers'][:15], 'pitching', pitcher_periods, max_workers=8)
            if away_roster.get('batters'):
                process_team_roster_in_parallel(away_roster['batters'][:15], 'hitting', hitter_periods, max_workers=8)
            if away_roster.get('pitchers'):
                process_team_roster_in_parallel(away_roster['pitchers'][:15], 'pitching', pitcher_periods, max_workers=8)

            logger.info(f"✓ Game {index}/{total} cached")

        except Exception as e:
            logger.error(f"Failed to warm game {index}: {e}", exc_info=True)


def warm_cache_on_startup(app):
    """Pre-loads data for all of today's games in parallel."""
    with app.app_context():
        try:
            logger.info("🔥 Warming cache for ALL today's games...")
            pacific_tz = pytz.timezone('US/Pacific')
            today_str = datetime.now(pacific_tz).strftime('%Y-%m-%d')
            games = MLBStatsAPI.get_todays_games(today_str)
            logger.info(f"Found {len(games)} games today.")

            # --- THROTTLE LIMIT TO PREVENT CRASHES ---
            with ThreadPoolExecutor(max_workers=1) as executor:
                for i, game in enumerate(games, 1):
                    executor.submit(warm_single_game, app, game, i, len(games))

            logger.info("✅ Cache warming complete!")

        except Exception as e:
            logger.error(f"❌ Cache warming failed: {e}", exc_info=True)


def daily_cache_refresh(app):
    """Clears and refreshes the cache once daily at 6 AM PST."""
    while True:
        try:
            pst = pytz.timezone('US/Pacific')
            now = datetime.now(pst)
            target_time = now.replace(hour=6, minute=0, second=0, microsecond=0)

            if now >= target_time:
                target_time += timedelta(days=1)

            wait_seconds = (target_time - now).total_seconds()
            logger.info(f"⏰ Next cache refresh at {target_time.strftime('%Y-%m-%d %I:%M %p PST')} ({wait_seconds/3600:.1f} hrs)")

            time.sleep(wait_seconds)

            logger.info("🌅 6 AM PST — Starting daily cache refresh...")
            with app.app_context():
                cache.clear()

            warm_cache_on_startup(app)

        except Exception as e:
            logger.error(f"❌ Daily refresh error: {e}", exc_info=True)
            time.sleep(3600)