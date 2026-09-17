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
- distinguish duplicate team names using tournament, country/category and team type when OddsPapi exposes that information
- see whether an ambiguous participant has an upcoming fixture with odds from the selected bookmaker
- follow up to 10 teams

Search results are **not filtered out** just because several participants have similar or identical names. The integration keeps the matches and adds context so you can decide which one is correct.

## Finding the right team

OddsPapi identifies every club and national team with a unique **participant ID**.

You normally do **not** need to find this ID manually. Search for the team by name during setup or through **Configure → Add team**, then select the correct result from the dropdown.

### Duplicate names are enriched before selection

Some OddsPapi participants have exactly the same displayed name. This can make a search such as `Bodø/Glimt` return several almost identical rows.

From version **1.0.1**, the integration detects duplicate normalized names and performs targeted fixture lookups **before the dropdown is shown**. When OddsPapi exposes enough metadata, a result can look like:

```text
Bodø/Glimt — Eliteserien, Norway, Pinnacle odds ✓ (ID 656)
Bodø/Glimt [Women] — Toppserien, Norway, no upcoming Pinnacle odds found (ID ...)
Bodø/Glimt [U21] — U21 competition, Norway, no upcoming Pinnacle odds found (ID ...)
Bodø/Glimt SRL (ID ...)
```

The exact text depends on the metadata OddsPapi returns for that participant.

The integration can derive labels such as:

- `Women`
- `U23`, `U21`, `U20`, `U19`, `U18`, `U17`, `U16`
- `Youth`
- `Reserves`
- `SRL`

If no useful upcoming fixture metadata is available, the participant is still shown with its raw OddsPapi name and ID instead of being hidden or guessed.

Known participant IDs used while testing this integration:

| Team | OddsPapi participant ID |
|---|---:|
| Manchester United | `35` |
| Norway national team | `4475` |
| Bodø/Glimt | `656` |

### Why can several similar teams appear?

OddsPapi can contain multiple participants with similar club or country names, including senior teams, women's teams, youth teams, reserve teams, SRL/simulated participants, and other provider-specific participants.

The integration intentionally keeps these results. It uses the OddsPapi fixture metadata only to make the dropdown easier to understand.

### Search enrichment and API quota

Team-search enrichment is designed for small API plans:

- unique-name search results do not trigger extra fixture enrichment lookups
- targeted enrichment is only used for duplicate normalized names
- results are cached while the current setup/options flow is open
- enrichment is capped at **8 fixture requests per config/options flow**

This prevents a search that returns many participants from creating one API request for every result.

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

The normal coordinator also uses one shared short fixture-window lookup where possible before falling back to participant-specific discovery.

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

If several identical team names appear, version 1.0.1 attempts to enrich those duplicate rows before selection. If a participant still only shows its raw name and ID, OddsPapi did not expose enough usable upcoming fixture metadata for that participant during the lookup.

## Security

The API key is entered through Home Assistant's config flow. Do not commit API keys to GitHub or include them in issues/screenshots.

## Version

Current version: **1.0.1**

## License

MIT License.
