"""Config flow for OddsPapi Sports Odds."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import re
from typing import Any
import unicodedata

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OddsPapiApi, OddsPapiAuthError, OddsPapiError, OddsPapiQuotaError
from .const import (
    CONF_ACTION,
    CONF_API_KEY,
    CONF_BOOKMAKER,
    CONF_PROFILE,
    CONF_REMOVE_TEAMS,
    CONF_SEARCH,
    CONF_TEAM,
    CONF_TEAMS,
    DEFAULT_BOOKMAKER,
    DEFAULT_PROFILE,
    DOMAIN,
    FIXTURE_WINDOW_DAYS,
    MAX_TEAMS,
    PROFILES,
)
from .helpers import active_subscription


def _bookmakers(account: dict[str, Any]) -> list[str]:
    subscription = active_subscription(account)
    bookmaker_map = subscription.get("bookmakers") or {}
    values = sorted(str(key) for key in bookmaker_map)
    return values or [DEFAULT_BOOKMAKER]


def _team_list(entry: ConfigEntry) -> list[dict[str, Any]]:
    teams = entry.options.get(CONF_TEAMS, entry.data.get(CONF_TEAMS, []))
    return [dict(team) for team in teams]


def _search_key(value: str) -> str:
    """Normalize names so e.g. Bodo/Glimt also matches Bodø/Glimt."""
    value = value.casefold().translate(
        str.maketrans(
            {
                "ø": "o",
                "æ": "ae",
                "å": "a",
            }
        )
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _match_sort_key(search: str, name: str) -> tuple[int, int, int, str]:
    candidate = _search_key(name)
    return (
        0 if candidate == search else 1,
        0 if candidate.startswith(search) else 1,
        len(candidate),
        candidate,
    )


def _build_participant_context(fixtures: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Build lightweight display context from the next known fixture."""
    context: dict[str, dict[str, str]] = {}
    for fixture in sorted(fixtures, key=lambda item: str(item.get("startTime") or "")):
        tournament = str(fixture.get("tournamentName") or "").strip()
        category = str(fixture.get("categoryName") or "").strip()
        for side in (1, 2):
            participant_id = str(fixture.get(f"participant{side}Id") or "").strip()
            if not participant_id or participant_id in context:
                continue
            participant_name = str(fixture.get(f"participant{side}Name") or "").strip()
            context[participant_id] = {
                "name": participant_name,
                "tournament": tournament,
                "category": category,
            }
    return context


def _team_type(name: str, tournament: str) -> str | None:
    """Infer a useful youth/women/reserve label from provider text only."""
    combined = f"{name} {tournament}".casefold().replace("-", " ")

    if re.search(r"\b(?:women|womens|women's|ladies|female)\b", combined):
        return "Women"

    for age in (23, 21, 20, 19, 18, 17, 16):
        if re.search(rf"\b(?:u\s*{age}|under\s*{age})\b", combined):
            return f"U{age}"

    if re.search(r"\breserves?\b", combined):
        return "Reserves"

    return None


def _participant_label(
    participant_id: str,
    name: str,
    context: dict[str, dict[str, str]],
) -> str:
    """Return a descriptive dropdown label without filtering any participant."""
    details = context.get(str(participant_id), {})
    display_name = details.get("name") or name
    tournament = details.get("tournament") or ""
    category = details.get("category") or ""

    team_type = _team_type(display_name, tournament)
    if team_type and _team_type(display_name, "") != team_type:
        display_name = f"{display_name} [{team_type}]"

    context_parts: list[str] = []
    if tournament:
        context_parts.append(tournament)
    if category and category.casefold() not in tournament.casefold():
        context_parts.append(category)

    if context_parts:
        return f"{display_name} — {', '.join(context_parts)} (ID {participant_id})"
    return f"{display_name} (ID {participant_id})"


class OddsPapiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._api: OddsPapiApi | None = None
        self._account: dict[str, Any] = {}
        self._bookmaker = DEFAULT_BOOKMAKER
        self._profile = DEFAULT_PROFILE
        self._participants: dict[str, str] | None = None
        self._participant_context: dict[str, dict[str, str]] = {}
        self._context_loaded = False
        self._selected: list[dict[str, Any]] = []
        self._matches: list[tuple[str, str]] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "OddsPapiOptionsFlow":
        return OddsPapiOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            api = OddsPapiApi(async_get_clientsession(self.hass), api_key)
            try:
                account = await api.async_get_account()
            except OddsPapiAuthError:
                errors["base"] = "invalid_auth"
            except OddsPapiError:
                errors["base"] = "cannot_connect"
            else:
                self._api_key = api_key
                self._api = api
                self._account = account
                subscription = active_subscription(account)
                unique_source = str(subscription.get("subscription_id") or account.get("current_subscription_id") or hashlib.sha256(api_key.encode()).hexdigest()[:16])
                await self.async_set_unique_id(unique_source)
                self._abort_if_unique_id_configured()
                return await self.async_step_settings()

        schema = vol.Schema({vol.Required(CONF_API_KEY): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._bookmaker = user_input[CONF_BOOKMAKER]
            self._profile = user_input[CONF_PROFILE]
            return await self.async_step_team_search()

        books = _bookmakers(self._account)
        bookmaker_options = [selector.SelectOptionDict(value=value, label=value.title()) for value in books]
        schema = vol.Schema({
            vol.Required(CONF_BOOKMAKER, default=DEFAULT_BOOKMAKER if DEFAULT_BOOKMAKER in books else books[0]): selector.SelectSelector(selector.SelectSelectorConfig(options=bookmaker_options, mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_PROFILE, default=DEFAULT_PROFILE): selector.SelectSelector(selector.SelectSelectorConfig(options=list(PROFILES), mode=selector.SelectSelectorMode.DROPDOWN, translation_key="refresh_profile")),
        })
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def _async_load_participants(self) -> bool:
        assert self._api is not None
        if self._participants is None:
            try:
                self._participants = await self._api.async_get_participants()
            except (OddsPapiError, OddsPapiQuotaError):
                return False

        if not self._context_loaded:
            self._context_loaded = True
            now = datetime.now(UTC)
            try:
                fixtures = await self._api.async_get_fixture_window(
                    now,
                    now + timedelta(days=FIXTURE_WINDOW_DAYS),
                )
            except OddsPapiError:
                pass
            else:
                self._participant_context = _build_participant_context(fixtures)

        return True

    async def async_step_team_search(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if not await self._async_load_participants():
            errors["base"] = "participants_failed"

        if user_input is not None and not errors:
            if user_input.get("finish"):
                if not self._selected:
                    errors["base"] = "select_team"
                else:
                    assert self._api_key is not None
                    return self.async_create_entry(title="OddsPapi Sports Odds", data={CONF_API_KEY: self._api_key, CONF_BOOKMAKER: self._bookmaker, CONF_PROFILE: self._profile, CONF_TEAMS: self._selected})
            else:
                search = _search_key(str(user_input.get(CONF_SEARCH, "")).strip())
                if not search:
                    errors[CONF_SEARCH] = "search_required"
                else:
                    selected_ids = {str(team["id"]) for team in self._selected}
                    matches = [
                        (participant_id, name)
                        for participant_id, name in (self._participants or {}).items()
                        if search in _search_key(name) and participant_id not in selected_ids
                    ]
                    matches.sort(key=lambda item: _match_sort_key(search, item[1]))
                    self._matches = matches[:50]
                    if not self._matches:
                        errors["base"] = "no_match"
                    else:
                        return await self.async_step_team_pick()

        selected = ", ".join(team["name"] for team in self._selected) or "—"
        schema = vol.Schema({vol.Optional(CONF_SEARCH, default=""): str, vol.Optional("finish", default=False): bool})
        return self.async_show_form(step_id="team_search", data_schema=schema, errors=errors, description_placeholders={"selected": selected, "max_teams": str(MAX_TEAMS)})

    async def async_step_team_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            participant_id = str(user_input[CONF_TEAM])
            name = dict(self._matches)[participant_id]
            if len(self._selected) < MAX_TEAMS:
                self._selected.append({"id": int(participant_id), "name": name})
            return await self.async_step_team_search()

        options = [
            selector.SelectOptionDict(
                value=participant_id,
                label=_participant_label(participant_id, name, self._participant_context),
            )
            for participant_id, name in self._matches
        ]
        return self.async_show_form(step_id="team_pick", data_schema=vol.Schema({vol.Required(CONF_TEAM): selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN))}))

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            api = OddsPapiApi(async_get_clientsession(self.hass), api_key)
            try:
                await api.async_get_account()
            except OddsPapiAuthError:
                errors["base"] = "invalid_auth"
            except OddsPapiError:
                errors["base"] = "cannot_connect"
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                assert entry is not None
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_KEY: api_key})

        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_API_KEY): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))}), errors=errors)


class OddsPapiOptionsFlow(OptionsFlowWithReload):
    def __init__(self) -> None:
        self._participants: dict[str, str] | None = None
        self._participant_context: dict[str, dict[str, str]] = {}
        self._context_loaded = False
        self._matches: list[tuple[str, str]] = []

    def _options(self) -> dict[str, Any]:
        options = deepcopy(dict(self.config_entry.options))
        options.setdefault(CONF_BOOKMAKER, self.config_entry.data.get(CONF_BOOKMAKER, DEFAULT_BOOKMAKER))
        options.setdefault(CONF_PROFILE, self.config_entry.data.get(CONF_PROFILE, DEFAULT_PROFILE))
        options.setdefault(CONF_TEAMS, _team_list(self.config_entry))
        return options

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            action = user_input[CONF_ACTION]
            if action == "settings":
                return await self.async_step_settings()
            if action == "add_team":
                return await self.async_step_add_team()
            return await self.async_step_remove_team()
        return self.async_show_form(step_id="init", data_schema=vol.Schema({vol.Required(CONF_ACTION): selector.SelectSelector(selector.SelectSelectorConfig(options=["settings", "add_team", "remove_team"], mode=selector.SelectSelectorMode.LIST, translation_key="options_action"))}))

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        options = self._options()
        errors: dict[str, str] = {}
        api = OddsPapiApi(async_get_clientsession(self.hass), self.config_entry.data[CONF_API_KEY])
        try:
            account = await api.async_get_account()
            bookmaker_values = _bookmakers(account)
        except OddsPapiError:
            bookmaker_values = [options[CONF_BOOKMAKER]]
            errors["base"] = "cannot_connect"

        if user_input is not None:
            options.update(user_input)
            return self.async_create_entry(data=options)

        schema = vol.Schema({
            vol.Required(CONF_BOOKMAKER, default=options[CONF_BOOKMAKER]): selector.SelectSelector(selector.SelectSelectorConfig(options=[selector.SelectOptionDict(value=value, label=value.title()) for value in bookmaker_values], mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_PROFILE, default=options[CONF_PROFILE]): selector.SelectSelector(selector.SelectSelectorConfig(options=list(PROFILES), mode=selector.SelectSelectorMode.DROPDOWN, translation_key="refresh_profile")),
        })
        return self.async_show_form(step_id="settings", data_schema=schema, errors=errors)

    async def _async_participants(self) -> bool:
        api = OddsPapiApi(async_get_clientsession(self.hass), self.config_entry.data[CONF_API_KEY])
        if self._participants is None:
            try:
                self._participants = await api.async_get_participants()
            except OddsPapiError:
                return False

        if not self._context_loaded:
            self._context_loaded = True
            now = datetime.now(UTC)
            try:
                fixtures = await api.async_get_fixture_window(
                    now,
                    now + timedelta(days=FIXTURE_WINDOW_DAYS),
                )
            except OddsPapiError:
                pass
            else:
                self._participant_context = _build_participant_context(fixtures)

        return True

    async def async_step_add_team(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if not await self._async_participants():
            errors["base"] = "participants_failed"
        teams = _team_list(self.config_entry)
        if len(teams) >= MAX_TEAMS:
            return self.async_abort(reason="max_teams")
        if user_input is not None and not errors:
            search = _search_key(str(user_input[CONF_SEARCH]).strip())
            existing = {str(team["id"]) for team in teams}
            matches = [
                (participant_id, name)
                for participant_id, name in (self._participants or {}).items()
                if search in _search_key(name) and participant_id not in existing
            ]
            matches.sort(key=lambda item: _match_sort_key(search, item[1]))
            self._matches = matches[:50]
            if not self._matches:
                errors["base"] = "no_match"
            else:
                return await self.async_step_add_team_pick()
        return self.async_show_form(step_id="add_team", data_schema=vol.Schema({vol.Required(CONF_SEARCH): str}), errors=errors)

    async def async_step_add_team_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            participant_id = str(user_input[CONF_TEAM])
            name = dict(self._matches)[participant_id]
            options = self._options()
            teams = [dict(team) for team in options[CONF_TEAMS]]
            teams.append({"id": int(participant_id), "name": name})
            options[CONF_TEAMS] = teams
            return self.async_create_entry(data=options)
        choices = [
            selector.SelectOptionDict(
                value=pid,
                label=_participant_label(pid, name, self._participant_context),
            )
            for pid, name in self._matches
        ]
        return self.async_show_form(step_id="add_team_pick", data_schema=vol.Schema({vol.Required(CONF_TEAM): selector.SelectSelector(selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.DROPDOWN))}))

    async def async_step_remove_team(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        teams = _team_list(self.config_entry)
        if not teams:
            return self.async_abort(reason="no_teams")
        mapping = {str(team["id"]): team["name"] for team in teams}
        if user_input is not None:
            remove = {str(item) for item in user_input[CONF_REMOVE_TEAMS]}
            remaining = [team for team in teams if str(team["id"]) not in remove]
            if not remaining:
                return self.async_show_form(step_id="remove_team", data_schema=vol.Schema({vol.Required(CONF_REMOVE_TEAMS): cv.multi_select(mapping)}), errors={"base": "keep_one_team"})
            options = self._options()
            options[CONF_TEAMS] = remaining
            return self.async_create_entry(data=options)
        return self.async_show_form(step_id="remove_team", data_schema=vol.Schema({vol.Required(CONF_REMOVE_TEAMS): cv.multi_select(mapping)}))
