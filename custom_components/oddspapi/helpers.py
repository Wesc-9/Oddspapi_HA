"""Pure helpers for OddsPapi data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def active_subscription(account: dict[str, Any]) -> dict[str, Any]:
    current_id = account.get("current_subscription_id")
    subscriptions = account.get("subscriptions") or []
    if current_id:
        for subscription in subscriptions:
            if subscription.get("subscription_id") == current_id:
                return subscription
    for subscription in subscriptions:
        if subscription.get("is_active"):
            return subscription
    return subscriptions[0] if subscriptions else {}


def fixture_participant_ids(fixture: dict[str, Any]) -> tuple[int, int]:
    try:
        p1 = int(fixture.get("participant1Id") or 0)
    except (TypeError, ValueError):
        p1 = 0
    try:
        p2 = int(fixture.get("participant2Id") or 0)
    except (TypeError, ValueError):
        p2 = 0
    return p1, p2


def select_next_fixture(fixtures: list[dict[str, Any]], participant_id: int) -> dict[str, Any] | None:
    now = datetime.now(UTC)
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for fixture in fixtures:
        p1, p2 = fixture_participant_ids(fixture)
        if participant_id not in (p1, p2):
            continue
        start = parse_datetime(fixture.get("startTime"))
        if start is None or start < now - timedelta(minutes=5):
            continue
        candidates.append((start, fixture))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _dict_key(mapping: dict[str, Any], key: str | int) -> dict[str, Any]:
    value = mapping.get(str(key))
    if isinstance(value, dict):
        return value
    value = mapping.get(key)  # type: ignore[arg-type]
    return value if isinstance(value, dict) else {}


def _price(outcomes: dict[str, Any], outcome_id: int) -> float | None:
    outcome = _dict_key(outcomes, outcome_id)
    players = outcome.get("players")
    if not isinstance(players, dict):
        return None
    player = _dict_key(players, 0)
    value = player.get("price")
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 1 else None


def _empty_odds() -> dict[str, float | None]:
    return {
        "home_odds": None,
        "draw_odds": None,
        "away_odds": None,
        "team_odds": None,
        "fair_home_probability": None,
        "fair_draw_probability": None,
        "fair_away_probability": None,
        "fair_win_probability": None,
    }


def parse_1x2_odds(odds: dict[str, Any], bookmaker: str, participant_id: int) -> dict[str, float | None]:
    bookmaker_odds = odds.get("bookmakerOdds")
    if not isinstance(bookmaker_odds, dict):
        return _empty_odds()
    bookmaker_data = bookmaker_odds.get(bookmaker)
    if not isinstance(bookmaker_data, dict):
        return _empty_odds()
    markets = bookmaker_data.get("markets")
    if not isinstance(markets, dict):
        return _empty_odds()
    market = _dict_key(markets, 101)
    outcomes = market.get("outcomes")
    if not isinstance(outcomes, dict):
        return _empty_odds()

    home = _price(outcomes, 101)
    draw = _price(outcomes, 102)
    away = _price(outcomes, 103)
    result = _empty_odds()
    result.update({"home_odds": home, "draw_odds": draw, "away_odds": away})

    if home and draw and away:
        implied = [1 / home, 1 / draw, 1 / away]
        total = sum(implied)
        if total > 0:
            result["fair_home_probability"] = implied[0] / total * 100
            result["fair_draw_probability"] = implied[1] / total * 100
            result["fair_away_probability"] = implied[2] / total * 100

    p1, p2 = fixture_participant_ids(odds)
    if participant_id == p1:
        result["team_odds"] = home
        result["fair_win_probability"] = result["fair_home_probability"]
    elif participant_id == p2:
        result["team_odds"] = away
        result["fair_win_probability"] = result["fair_away_probability"]
    return result


def build_team_data(team: dict[str, Any], fixture: dict[str, Any] | None, parsed_odds: dict[str, float | None] | None, bookmaker: str) -> dict[str, Any]:
    participant_id = int(team["id"])
    name = str(team["name"])
    result: dict[str, Any] = {
        "participant_id": participant_id,
        "name": name,
        "bookmaker": bookmaker,
        "fixture_id": None,
        "bookmaker_event_id": None,
        "kickoff": None,
        "home_team": None,
        "away_team": None,
        "next_opponent": None,
        **_empty_odds(),
    }
    if fixture is None:
        return result

    result["fixture_id"] = fixture.get("fixtureId")
    result["kickoff"] = fixture.get("startTime")
    result["home_team"] = fixture.get("participant1Name")
    result["away_team"] = fixture.get("participant2Name")
    providers = fixture.get("externalProviders")
    if isinstance(providers, dict):
        result["bookmaker_event_id"] = providers.get(f"{bookmaker}Id")
        if bookmaker == "pinnacle":
            result["bookmaker_event_id"] = providers.get("pinnacleId")

    p1, p2 = fixture_participant_ids(fixture)
    if participant_id == p1:
        result["next_opponent"] = fixture.get("participant2Name")
    elif participant_id == p2:
        result["next_opponent"] = fixture.get("participant1Name")
    if parsed_odds:
        result.update(parsed_odds)
    return result
