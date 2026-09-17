"""Sensor platform for OddsPapi Sports Odds."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import OddsPapiCoordinator
from .helpers import parse_datetime


@dataclass(frozen=True, kw_only=True)
class OddsPapiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


ACCOUNT_SENSORS: tuple[OddsPapiSensorDescription, ...] = (
    OddsPapiSensorDescription(key="quota_used", name="API requests used", icon="mdi:counter", entity_category=EntityCategory.DIAGNOSTIC, state_class=SensorStateClass.TOTAL, value_fn=lambda data: data["account"].get("request_used")),
    OddsPapiSensorDescription(key="quota_limit", name="API request limit", icon="mdi:gauge-full", entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda data: data["account"].get("request_limit")),
    OddsPapiSensorDescription(key="quota_remaining", name="API requests remaining", icon="mdi:gauge", entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda data: data["account"].get("request_remaining")),
)

TEAM_SENSORS: tuple[OddsPapiSensorDescription, ...] = (
    OddsPapiSensorDescription(key="next_opponent", name="Next opponent", icon="mdi:soccer", value_fn=lambda team: team.get("next_opponent")),
    OddsPapiSensorDescription(key="kickoff", name="Kickoff", device_class=SensorDeviceClass.TIMESTAMP, value_fn=lambda team: parse_datetime(team.get("kickoff"))),
    OddsPapiSensorDescription(key="home_team", name="Home team", icon="mdi:home", value_fn=lambda team: team.get("home_team")),
    OddsPapiSensorDescription(key="away_team", name="Away team", icon="mdi:airplane", value_fn=lambda team: team.get("away_team")),
    OddsPapiSensorDescription(key="home_odds", name="Home odds", icon="mdi:numeric-1-box", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda team: team.get("home_odds")),
    OddsPapiSensorDescription(key="draw_odds", name="Draw odds", icon="mdi:numeric-0-box", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda team: team.get("draw_odds")),
    OddsPapiSensorDescription(key="away_odds", name="Away odds", icon="mdi:numeric-2-box", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda team: team.get("away_odds")),
    OddsPapiSensorDescription(key="team_odds", name="Team odds", icon="mdi:chart-line", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda team: team.get("team_odds")),
    OddsPapiSensorDescription(key="fair_win_probability", name="Fair win probability", icon="mdi:percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda team: round(team["fair_win_probability"], 1) if team.get("fair_win_probability") is not None else None),
    OddsPapiSensorDescription(key="fixture_id", name="Fixture ID", icon="mdi:identifier", entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda team: team.get("fixture_id")),
    OddsPapiSensorDescription(key="bookmaker_event_id", name="Bookmaker event ID", icon="mdi:identifier", entity_category=EntityCategory.DIAGNOSTIC, value_fn=lambda team: team.get("bookmaker_event_id")),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: OddsPapiCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [OddsPapiAccountSensor(coordinator, entry, description) for description in ACCOUNT_SENSORS]
    for team_id in coordinator.data.get("teams", {}):
        entities.extend(OddsPapiTeamSensor(coordinator, entry, team_id, description) for description in TEAM_SENSORS)
    async_add_entities(entities)


class OddsPapiAccountSensor(CoordinatorEntity[OddsPapiCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: OddsPapiCoordinator, entry: ConfigEntry, description: OddsPapiSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry.entry_id}:account")}, name=NAME, manufacturer="OddsPapi", model="Sports Odds API")

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)


class OddsPapiTeamSensor(CoordinatorEntity[OddsPapiCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: OddsPapiCoordinator, entry: ConfigEntry, team_id: str, description: OddsPapiSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._team_id = team_id
        self._attr_unique_id = f"{entry.entry_id}_{team_id}_{description.key}"
        team = coordinator.data["teams"][team_id]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry.entry_id}:team:{team_id}")}, name=team.get("name", team_id), manufacturer="OddsPapi", model=f"{coordinator.bookmaker.title()} football odds")

    @property
    def native_value(self) -> Any:
        team = self.coordinator.data.get("teams", {}).get(self._team_id, {})
        value = self.entity_description.value_fn(team)
        if isinstance(value, datetime):
            return value
        return value
