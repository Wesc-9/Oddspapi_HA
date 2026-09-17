"""DataUpdateCoordinator for OddsPapi Sports Odds."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OddsPapiApi, OddsPapiAuthError, OddsPapiError, OddsPapiQuotaError
from .const import (
    CONF_BOOKMAKER,
    CONF_PROFILE,
    CONF_TEAMS,
    COORDINATOR_INTERVAL,
    DEFAULT_BOOKMAKER,
    DEFAULT_PROFILE,
    DOMAIN,
    FIXTURE_WINDOW_DAYS,
    GLOBAL_FIXTURE_REFRESH,
    MIN_QUOTA_RESERVE,
    MISSING_FIXTURE_REFRESH,
    ODDS_INTERVALS,
    POST_MATCH_GRACE,
    QUOTA_RESERVE_PERCENT,
)
from .helpers import (
    active_subscription,
    build_team_data,
    parse_1x2_odds,
    parse_datetime,
    select_next_fixture,
)

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _age(value: str | None, now: datetime) -> timedelta | None:
    parsed = parse_datetime(value)
    return now - parsed if parsed else None


class OddsPapiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate quota-aware fixture and odds polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: OddsPapiApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=COORDINATOR_INTERVAL)
        self.entry = entry
        self.api = api
        self.store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.cache: dict[str, Any] = {}

    @property
    def bookmaker(self) -> str:
        return str(self.entry.options.get(CONF_BOOKMAKER, self.entry.data.get(CONF_BOOKMAKER, DEFAULT_BOOKMAKER)))

    @property
    def profile(self) -> str:
        return str(self.entry.options.get(CONF_PROFILE, self.entry.data.get(CONF_PROFILE, DEFAULT_PROFILE)))

    @property
    def teams(self) -> list[dict[str, Any]]:
        teams = self.entry.options.get(CONF_TEAMS, self.entry.data.get(CONF_TEAMS, []))
        return [dict(team) for team in teams]

    async def _async_setup(self) -> None:
        self.cache = await self.store.async_load() or {}
        self.cache.setdefault("teams", {})
        self.cache.setdefault("meta", {})
        self.cache.setdefault("account", {})
        self._sync_team_cache()

    def _sync_team_cache(self) -> None:
        team_cache = self.cache.setdefault("teams", {})
        configured_ids = {str(team["id"]) for team in self.teams}
        for team_id in list(team_cache):
            if team_id not in configured_ids:
                del team_cache[team_id]
        for team in self.teams:
            team_id = str(team["id"])
            entry = team_cache.setdefault(team_id, {})
            entry["name"] = team["name"]
            entry["participant_id"] = int(team["id"])
            entry.setdefault("fixture", None)
            entry.setdefault("odds", None)
            entry.setdefault("last_individual_fixture_lookup", None)
            entry.setdefault("last_odds_update", None)

    def _quota(self, account: dict[str, Any], spent: int = 0) -> tuple[int, int, int]:
        subscription = active_subscription(account)
        try:
            limit = int(subscription.get("request_limit") or 0)
        except (TypeError, ValueError):
            limit = 0
        try:
            count = int(subscription.get("request_count") or 0) + spent
        except (TypeError, ValueError):
            count = spent
        remaining = max(limit - count, 0) if limit else 999999
        return count, limit, remaining

    def _can_spend(self, account: dict[str, Any], spent: int, calls: int = 1) -> bool:
        count, limit, _remaining = self._quota(account, spent)
        if not limit:
            return True
        reserve = max(MIN_QUOTA_RESERVE, int(limit * QUOTA_RESERVE_PERCENT))
        return count + calls <= max(limit - reserve, 0)

    def _odds_interval(self, kickoff: datetime, now: datetime) -> timedelta:
        until = kickoff - now
        for threshold, interval in ODDS_INTERVALS.get(self.profile, ODDS_INTERVALS[DEFAULT_PROFILE]):
            if threshold is None or until <= threshold:
                return interval
        return timedelta(hours=48)

    def _fixture_is_expired(self, fixture: dict[str, Any] | None, now: datetime) -> bool:
        if not fixture:
            return True
        kickoff = parse_datetime(fixture.get("startTime"))
        if kickoff is None:
            return True
        return now > kickoff + POST_MATCH_GRACE

    def _set_fixture(self, team_id: str, fixture: dict[str, Any]) -> None:
        state = self.cache["teams"][team_id]
        old_id = (state.get("fixture") or {}).get("fixtureId")
        new_id = fixture.get("fixtureId")
        state["fixture"] = fixture
        if old_id != new_id:
            state["odds"] = None
            state["last_odds_update"] = None

    async def _async_update_data(self) -> dict[str, Any]:
        now = _now()
        self._sync_team_cache()
        try:
            account = await self.api.async_get_account()
        except OddsPapiAuthError as err:
            raise ConfigEntryAuthFailed("OddsPapi API key is no longer valid") from err
        except OddsPapiError as err:
            account = self.cache.get("account") or {}
            if not account:
                raise UpdateFailed(str(err)) from err
            _LOGGER.debug("Using cached account data after account error: %s", err)

        spent = 0
        team_cache: dict[str, Any] = self.cache["teams"]
        meta = self.cache.setdefault("meta", {})
        last_window = parse_datetime(meta.get("last_fixture_window"))
        global_due = last_window is None or now - last_window >= GLOBAL_FIXTURE_REFRESH
        for state in team_cache.values():
            fixture = state.get("fixture")
            if fixture and self._fixture_is_expired(fixture, now):
                kickoff = parse_datetime(fixture.get("startTime"))
                if kickoff and (last_window is None or last_window < kickoff + POST_MATCH_GRACE):
                    global_due = True
                    break

        if global_due and self._can_spend(account, spent):
            try:
                fixtures = await self.api.async_get_fixture_window(now, now + timedelta(days=FIXTURE_WINDOW_DAYS))
                spent += 1
                meta["last_fixture_window"] = _iso(now)
                for team in self.teams:
                    team_id = str(team["id"])
                    fixture = select_next_fixture(fixtures, int(team["id"]))
                    if fixture is not None:
                        self._set_fixture(team_id, fixture)
                    elif self._fixture_is_expired(team_cache[team_id].get("fixture"), now):
                        team_cache[team_id]["fixture"] = None
                        team_cache[team_id]["odds"] = None
            except OddsPapiQuotaError:
                _LOGGER.warning("OddsPapi quota guard: fixture refresh was rejected")
            except OddsPapiAuthError as err:
                raise ConfigEntryAuthFailed("OddsPapi API key is no longer valid") from err
            except OddsPapiError as err:
                _LOGGER.debug("Fixture window refresh failed: %s", err)

        for team in self.teams:
            team_id = str(team["id"])
            state = team_cache[team_id]
            if not self._fixture_is_expired(state.get("fixture"), now):
                continue
            last_lookup_age = _age(state.get("last_individual_fixture_lookup"), now)
            if last_lookup_age is not None and last_lookup_age < MISSING_FIXTURE_REFRESH:
                continue
            if not self._can_spend(account, spent):
                break
            try:
                fixtures = await self.api.async_get_participant_fixtures(int(team["id"]), now)
                spent += 1
                state["last_individual_fixture_lookup"] = _iso(now)
                fixture = select_next_fixture(fixtures, int(team["id"]))
                if fixture is not None:
                    self._set_fixture(team_id, fixture)
            except OddsPapiQuotaError:
                break
            except OddsPapiAuthError as err:
                raise ConfigEntryAuthFailed("OddsPapi API key is no longer valid") from err
            except OddsPapiError as err:
                _LOGGER.debug("Participant fixture lookup failed for %s: %s", team_id, err)

        for team in self.teams:
            team_id = str(team["id"])
            state = team_cache[team_id]
            fixture = state.get("fixture")
            if not fixture:
                continue
            kickoff = parse_datetime(fixture.get("startTime"))
            if kickoff is None or kickoff <= now:
                continue
            interval = self._odds_interval(kickoff, now)
            last_odds_age = _age(state.get("last_odds_update"), now)
            if last_odds_age is not None and last_odds_age < interval:
                continue
            if not self._can_spend(account, spent):
                break
            fixture_id = fixture.get("fixtureId")
            if not isinstance(fixture_id, str) or not fixture_id:
                continue
            try:
                odds = await self.api.async_get_odds(fixture_id, self.bookmaker)
                spent += 1
                state["odds"] = odds
                state["last_odds_update"] = _iso(now)
            except OddsPapiQuotaError:
                break
            except OddsPapiAuthError as err:
                raise ConfigEntryAuthFailed("OddsPapi API key is no longer valid") from err
            except OddsPapiError as err:
                _LOGGER.debug("Odds refresh failed for %s: %s", team_id, err)

        account_display = deepcopy(account)
        subscription = active_subscription(account_display)
        if subscription and spent:
            try:
                subscription["request_count"] = int(subscription.get("request_count") or 0) + spent
            except (TypeError, ValueError):
                pass
        self.cache["account"] = account_display
        meta["last_update"] = _iso(now)
        await self.store.async_save(self.cache)
        return self._build_data(account_display)

    def _build_data(self, account: dict[str, Any]) -> dict[str, Any]:
        subscription = active_subscription(account)
        try:
            limit = int(subscription.get("request_limit") or 0)
        except (TypeError, ValueError):
            limit = 0
        try:
            used = int(subscription.get("request_count") or 0)
        except (TypeError, ValueError):
            used = 0
        teams: dict[str, Any] = {}
        for team in self.teams:
            team_id = str(team["id"])
            cached = self.cache["teams"].get(team_id, {})
            fixture = cached.get("fixture")
            raw_odds = cached.get("odds")
            parsed_odds = parse_1x2_odds(raw_odds, self.bookmaker, int(team["id"])) if isinstance(raw_odds, dict) else None
            teams[team_id] = build_team_data(team, fixture, parsed_odds, self.bookmaker)
        return {
            "account": {
                "request_used": used,
                "request_limit": limit,
                "request_remaining": max(limit - used, 0) if limit else None,
                "last_request": subscription.get("last_request"),
                "bookmaker": self.bookmaker,
                "profile": self.profile,
            },
            "teams": teams,
            "meta": deepcopy(self.cache.get("meta", {})),
        }
