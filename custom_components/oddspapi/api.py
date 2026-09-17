"""Async client for OddsPapi v4."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import SPORT_ID_SOCCER

BASE_URL = "https://api.oddspapi.io/v4"


class OddsPapiError(Exception):
    """Base OddsPapi error."""


class OddsPapiAuthError(OddsPapiError):
    """Authentication failed."""


class OddsPapiQuotaError(OddsPapiError):
    """Quota exhausted."""


class OddsPapiApi:
    """Small async OddsPapi API client."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key
        self._lock = asyncio.Lock()
        self._last_request: dict[str, float] = {}

    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.isoformat(timespec="seconds").replace("+00:00", "Z")

    async def _throttle(self, bucket: str, minimum_delay: float) -> None:
        now = asyncio.get_running_loop().time()
        last = self._last_request.get(bucket, 0.0)
        wait = minimum_delay - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request[bucket] = asyncio.get_running_loop().time()

    async def _get(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
        bucket: str = "default",
        minimum_delay: float = 0.75,
    ) -> Any:
        query = dict(params or {})
        query["apiKey"] = self._api_key
        async with self._lock:
            await self._throttle(bucket, minimum_delay)
            try:
                async with self._session.get(
                    f"{BASE_URL}/{endpoint}",
                    params=query,
                    timeout=ClientTimeout(total=45),
                ) as response:
                    if response.status in (401, 403):
                        raise OddsPapiAuthError("OddsPapi rejected the API key")
                    if response.status == 429:
                        raise OddsPapiQuotaError("OddsPapi request quota exhausted")
                    if response.status >= 400:
                        text = (await response.text())[:500]
                        raise OddsPapiError(
                            f"OddsPapi returned HTTP {response.status}: {text}"
                        )
                    return await response.json()
            except (ClientError, asyncio.TimeoutError) as err:
                raise OddsPapiError(f"Unable to reach OddsPapi: {err}") from err

    async def async_get_account(self) -> dict[str, Any]:
        data = await self._get("account", bucket="account", minimum_delay=1.05)
        if not isinstance(data, dict):
            raise OddsPapiError("Unexpected /account response")
        return data

    async def async_get_participants(self) -> dict[str, str]:
        data = await self._get(
            "participants",
            params={"sportId": SPORT_ID_SOCCER, "language": "en"},
            bucket="participants",
            minimum_delay=1.05,
        )
        if not isinstance(data, dict):
            raise OddsPapiError("Unexpected /participants response")
        return {str(key): str(value) for key, value in data.items()}

    async def async_get_fixture_window(
        self,
        start: datetime,
        end: datetime,
        bookmaker: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "sportId": SPORT_ID_SOCCER,
            "from": self._iso(start),
            "to": self._iso(end),
            "statusId": 0,
            "language": "en",
        }
        if bookmaker:
            params.update({"hasOdds": "true", "bookmakers": bookmaker})

        data = await self._get(
            "fixtures",
            params=params,
            bucket="fixtures",
            minimum_delay=2.05,
        )
        if not isinstance(data, list):
            raise OddsPapiError("Unexpected /fixtures response")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_participant_fixtures(
        self,
        participant_id: int,
        start: datetime,
        bookmaker: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "participantId": participant_id,
            "from": self._iso(start),
            "statusId": 0,
            "language": "en",
        }
        if bookmaker:
            params.update({"hasOdds": "true", "bookmakers": bookmaker})

        data = await self._get(
            "fixtures",
            params=params,
            bucket="fixtures",
            minimum_delay=2.05,
        )
        if not isinstance(data, list):
            raise OddsPapiError("Unexpected participant fixture response")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_odds(self, fixture_id: str, bookmaker: str) -> dict[str, Any]:
        data = await self._get(
            "odds",
            params={
                "fixtureId": fixture_id,
                "bookmakers": bookmaker,
                "oddsFormat": "decimal",
                "language": "en",
                "verbosity": 3,
            },
            bucket="odds",
            minimum_delay=0.8,
        )
        if not isinstance(data, dict):
            raise OddsPapiError("Unexpected /odds response")
        return data
