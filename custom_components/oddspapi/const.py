"""Constants for the OddsPapi Sports Odds integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "oddspapi"
NAME = "OddsPapi Sports Odds"
VERSION = "1.0.1"

CONF_API_KEY = "api_key"
CONF_BOOKMAKER = "bookmaker"
CONF_PROFILE = "profile"
CONF_TEAMS = "teams"
CONF_SEARCH = "search"
CONF_TEAM = "team"
CONF_ACTION = "action"
CONF_REMOVE_TEAMS = "remove_teams"

SPORT_ID_SOCCER = 10
DEFAULT_BOOKMAKER = "pinnacle"
MAX_TEAMS = 10
FIXTURE_WINDOW_DAYS = 9

PROFILE_LOW = "low"
PROFILE_BALANCED = "balanced"
PROFILE_FREQUENT = "frequent"
DEFAULT_PROFILE = PROFILE_BALANCED
PROFILES = (PROFILE_LOW, PROFILE_BALANCED, PROFILE_FREQUENT)

COORDINATOR_INTERVAL = timedelta(hours=1)
GLOBAL_FIXTURE_REFRESH = timedelta(hours=24)
MISSING_FIXTURE_REFRESH = timedelta(days=3)
POST_MATCH_GRACE = timedelta(hours=3)

ACCOUNT_REFRESH = timedelta(hours=1)
QUOTA_RESERVE_PERCENT = 0.20
MIN_QUOTA_RESERVE = 25

ODDS_INTERVALS = {
    PROFILE_LOW: (
        (timedelta(hours=12), timedelta(hours=6)),
        (timedelta(hours=72), timedelta(hours=24)),
        (None, timedelta(hours=72)),
    ),
    PROFILE_BALANCED: (
        (timedelta(hours=12), timedelta(hours=3)),
        (timedelta(hours=72), timedelta(hours=12)),
        (None, timedelta(hours=48)),
    ),
    PROFILE_FREQUENT: (
        (timedelta(hours=12), timedelta(hours=1)),
        (timedelta(hours=72), timedelta(hours=6)),
        (None, timedelta(hours=24)),
    ),
}

PLATFORMS = ["sensor"]
