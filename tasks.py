# tasks.py
"""
Background caching tasks for the application.
"""
import time
import logging
from datetime import datetime, timedelta
import pytz

from mlb_api import MLBStatsAPI
from extensions import cache
# FIX: Import the new, more efficient function
from utils import process_team_roster_in_parallel

logger = logging.getLogger(__name__)

def warm_cache_on_startup(app):
    """
    Pre-loads data for all of today's games into the cache on startup.
    This runs inside the app context.
    """
    with app.app_context():
        try:
            logger.info("🔥 Warming cache for ALL today's games...")
            pacific_tz = pytz.timezone('US/Pacific')
            today_str = datetime.now(pacific_tz).strftime('%Y-%m-%d')
            games = MLBStatsAPI.get_todays_games(today_str)
            
            logger.info(f"Found {len(games)} games today.")
            
            # Define periods to pre-cache
            hitter_periods = {'7': 7, '10': 10, '21': 21}
            pitcher_periods = {'7': 2, '10': 3, '21': 4}
            
            for i, game in enumerate(games):
                if 'postponed' in game.get('status', {}).get('detailedState', '').lower():
                    logger.info(f"⏭️ Skipping postponed game.")
                    continue
                
                home_id = game['teams']['home']['team']['id']
                away_id = game['teams']['away']['team']['id']
                logger.info(f"Loading game {i+1}/{len(games)}: {game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}...")

                home_roster = MLBStatsAPI.get_team_roster(home_id)
                away_roster = MLBStatsAPI.get_team_roster(away_id)

                # FIX: Use the new function to cache all periods at once, with fewer workers
                if home_roster.get('batters'):
                    process_team_roster_in_parallel(home_roster['batters'][:15], 'hitting', hitter_periods, max_workers=5)
                if home_roster.get('pitchers'):
                    process_team_roster_in_parallel(home_roster['pitchers'][:15], 'pitching', pitcher_periods, max_workers=5)
                
                if away_roster.get('batters'):
                    process_team_roster_in_parallel(away_roster['batters'][:15], 'hitting', hitter_periods, max_workers=5)
                if away_roster.get('pitchers'):
                    process_team_roster_in_parallel(away_roster['pitchers'][:15], 'pitching', pitcher_periods, max_workers=5)

                logger.info(f" ✓ Cached initial data for game {i+1}")
                time.sleep(5) # Increased delay to further avoid rate limits

            logger.info("✅ Cache warming complete for ALL games!")
            
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
            
            logger.info(f"⏰ Next cache refresh scheduled for {target_time.strftime('%Y-%m-%d %I:%M %p PST')}")
            logger.info(f"   Waiting {wait_seconds/3600:.1f} hours...")
            
            time.sleep(wait_seconds)
            
            logger.info("\n🌅 6 AM PST - Starting daily cache refresh...")
            with app.app_context():
                cache.clear()
            
            warm_cache_on_startup(app)
            
        except Exception as e:
            logger.error(f"❌ Daily refresh error: {e}", exc_info=True)
            time.sleep(3600)
