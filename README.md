# OddsPapi Sports Odds for Home Assistant

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Wesc-9&repository=Oddspapi_HA&category=integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=oddspapi)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://www.hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/Wesc-9/Oddspapi_HA)](LICENSE)

A quota-aware Home Assistant custom integration for football odds powered by OddsPapi.

> Unofficial community integration. This project is not affiliated with OddsPapi, Home Assistant, HACS, Pinnacle, or any bookmaker.

## Install

### 1. Open in HACS

Click the button above, or add this repository manually in **HACS → Integrations → Custom repositories**:

```text
https://github.com/Wesc-9/Oddspapi_HA
```

Category: **Integration**.

Download the integration and restart Home Assistant.

### 2. Add the integration

After restart, click **Add Integration** above, or go to:

**Settings → Devices & services → Add integration → OddsPapi Sports Odds**

No YAML is required.

## Setup flow

The UI setup lets you:

- enter and validate your OddsPapi API key
- choose a bookmaker
- choose a refresh profile
- search for football clubs and national teams
- follow up to 10 teams

## Sensors

The integration creates account-level quota sensors and per-team sensors for:

- next opponent
- kickoff
- home team
- away team
- home odds
- draw odds
- away odds
- selected-team odds
- fair win probability
- fixture ID
- bookmaker event ID

## Quota-aware polling

The integration caches fixtures and odds and uses slower refresh intervals when a match is farther away. It also keeps a quota reserve so a small monthly plan is less likely to be exhausted by polling.

Available profiles:

| Profile | Under 12 h | 12–72 h | Farther away |
|---|---:|---:|---:|
| Low usage | 6 h | 24 h | 72 h |
| Balanced | 3 h | 12 h | 48 h |
| Frequent | 1 h | 6 h | 24 h |

The integration also uses one shared short fixture-window lookup where possible before falling back to participant-specific discovery.

## Fair win probability

The Home/Draw/Away market is normalized to remove the bookmaker margin:

```text
home = 1 / home_odds
draw = 1 / draw_odds
away = 1 / away_odds

total = home + draw + away
fair_home = home / total
fair_draw = draw / total
fair_away = away / total
```

This is a market-implied probability, not a betting recommendation.

## Repository structure

```text
custom_components/
└── oddspapi/
    ├── __init__.py
    ├── api.py
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── diagnostics.py
    ├── helpers.py
    ├── manifest.json
    ├── sensor.py
    ├── strings.json
    └── translations/
        ├── en.json
        └── nb.json
```

## Migrating from the old YAML setup

Once this integration works, disable any old REST/package YAML that also calls OddsPapi. Running both systems in parallel can unnecessarily consume API quota.

## Troubleshooting

If HACS says the repository structure is not compliant, verify that `custom_components/oddspapi/manifest.json` exists on the branch/tag you are installing.

If **Add Integration** does not find OddsPapi, make sure HACS finished installing the custom component and restart Home Assistant first.

## Security

The API key is entered through Home Assistant's config flow. Do not commit API keys to GitHub or include them in issues/screenshots.

## Version

Current development version: **0.1.2**

## License

MIT License.
