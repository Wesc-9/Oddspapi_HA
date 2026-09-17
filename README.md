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
- see the OddsPapi participant ID for every search result
- see extra team context such as competition, country/category, Women, U21, U19, etc. when OddsPapi has upcoming fixture metadata available
- follow up to 10 teams

Search results are not filtered out just because several teams have similar names. The integration keeps the available matches and tries to make them easier to distinguish.

## Finding the right team

OddsPapi identifies every club and national team with a unique **participant ID**.

You normally do **not** need to find this ID manually. Search for the team by name during setup and select the correct result from the dropdown.

The integration always shows the participant ID and, when possible, enriches the result with metadata from an upcoming fixture.

Examples may look like:

```text
Manchester United — Premier League, England (ID 35)
Norway — UEFA competition, International (ID 4475)
Bodø/Glimt — Eliteserien, Norway (ID 656)
Example FC [Women] — Women's competition, Norway (ID ...)
Example FC U21 — U21 competition, England (ID ...)
```

Known participant IDs used while testing this integration:

| Team | OddsPapi participant ID |
|---|---:|
| Manchester United | `35` |
| Norway national team | `4475` |
| Bodø/Glimt | `656` |

### Why can several similar teams appear?

OddsPapi can contain multiple participants with similar club or country names, for example:

- senior team
- women's team
- U23 / U21 / U20 / U19 / other youth teams
- reserve teams
- other provider-specific participants with a similar name

The integration intentionally does **not** hide those results. Instead it:

1. puts the closest name match first
2. keeps the original OddsPapi participant ID visible
3. uses upcoming fixture metadata to show tournament/category context when available
4. adds a `Women`, `U21`, `U19`, etc. label when that information can be derived from the participant or tournament name

If OddsPapi has no upcoming fixture metadata for a participant, the result falls back to:

```text
Team name (ID 1234)
```

This avoids guessing.

### Searching with special characters

Team search normalizes common punctuation and Scandinavian characters, so searches such as `Bodo Glimt`, `Bodø/Glimt`, and similar variants are easier to match.

### Finding an ID manually

OddsPapi's participant endpoint for football is:

```text
GET /v4/participants?sportId=10&language=en
```

The response is an object where the key is the participant ID and the value is the participant name, for example:

```json
{
  "35": "Manchester United",
  "4475": "Norway",
  "656": "Bodø/Glimt"
}
```

> **Important:** Use the OddsPapi participant ID. It is not the same as a Pinnacle, SofaScore, Flashscore, or other provider ID.

## Bookmaker compatibility

The integration lets you select bookmakers made available by your OddsPapi subscription.

At this stage, the integration has only been **tested and verified with Pinnacle**.

Known working test examples include:

- Manchester United (`35`)
- Norway national team (`4475`)
- Bodø/Glimt (`656`)

Other bookmakers may work, but they have not yet been verified with this integration.

If you successfully test another bookmaker, feel free to open an issue or contribute your results.

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

Team-search enrichment also uses a shared fixture lookup for the setup session instead of making one request per search result.

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

If several similar team names appear, use the displayed tournament/category and participant ID to identify the correct participant. When no context is available, the integration deliberately shows the raw OddsPapi name and ID instead of guessing.

## Security

The API key is entered through Home Assistant's config flow. Do not commit API keys to GitHub or include them in issues/screenshots.

## Version

Current stable version: **1.0.0**

## License

MIT License.
