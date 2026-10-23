"""
Wind Intelligence — Elexon API client.

HTTP client for fetching FUELHH and WINDFOR datasets from the
Elexon Insights Solution API.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import Settings, get_settings
from app.models.domain import FuelhhRecord, WindforRecord

logger = logging.getLogger(__name__)


def parse_utc_iso(dt_str: str) -> datetime:
    """Parse an ISO 8601 string into a timezone-aware UTC datetime."""
    if not dt_str:
        raise ValueError("Datetime string cannot be empty")
    # Python 3.11+ supports 'Z' natively in fromisoformat, but replacing ensures compatibility
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ElexonClient:
    """Async client for interacting with Elexon BMRS API v1."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.elexon_base_url.rstrip("/")
        self._external_client = client
        # In-memory cache for fetched datasets
        self._fuelhh_cache: Dict[str, List[FuelhhRecord]] = {}
        self._windfor_cache: Dict[str, List[WindforRecord]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=30.0)

    async def _request_with_retry(
        self, endpoint: str, params: Dict[str, Any], max_retries: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Execute GET request with exponential backoff on HTTP 429 and transient 5xx errors.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        delay = 1.0
        client = await self._get_client()
        should_close = self._external_client is None

        try:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        return response.json()

                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                        wait_time = float(retry_after) if retry_after else delay
                        logger.warning(
                            "Elexon API returned %d on %s. Retrying in %.2fs (attempt %d/%d)...",
                            response.status_code,
                            endpoint,
                            wait_time,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(wait_time)
                        delay *= 2
                        continue

                    response.raise_for_status()

                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(
                        "Network error %s contacting Elexon API. Retrying in %.2fs...",
                        str(e),
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2

            raise httpx.HTTPStatusError(
                f"Failed to fetch {endpoint} after {max_retries} attempts",
                request=response.request,
                response=response,
            )
        finally:
            if should_close:
                await client.aclose()

    async def fetch_fuelhh_wind(
        self, settlement_date_from: str, settlement_date_to: str
    ) -> List[FuelhhRecord]:
        """
        Fetch FUELHH dataset filtered to WIND fuel type for settlement dates in [from, to].
        Cached by settlement date range.
        """
        cache_key = f"{settlement_date_from}_{settlement_date_to}"
        if cache_key in self._fuelhh_cache:
            return self._fuelhh_cache[cache_key]

        raw_records = await self._request_with_retry(
            "datasets/FUELHH/stream",
            params={
                "settlementDateFrom": settlement_date_from,
                "settlementDateTo": settlement_date_to,
            },
        )

        wind_records: List[FuelhhRecord] = []
        for r in raw_records:
            if r.get("fuelType") != "WIND":
                continue
            try:
                wind_records.append(
                    FuelhhRecord(
                        dataset=r.get("dataset", "FUELHH"),
                        publish_time=parse_utc_iso(r["publishTime"]),
                        start_time=parse_utc_iso(r["startTime"]),
                        settlement_date=r["settlementDate"],
                        settlement_period=int(r["settlementPeriod"]),
                        fuel_type=r["fuelType"],
                        generation=int(r.get("generation", 0)),
                    )
                )
            except (KeyError, ValueError, TypeError) as ex:
                logger.debug("Skipping malformed FUELHH record %s: %s", r, ex)

        self._fuelhh_cache[cache_key] = wind_records
        return wind_records

    async def fetch_windfor(
        self, publish_datetime_from: str, publish_datetime_to: str
    ) -> List[WindforRecord]:
        """
        Fetch WINDFOR forecast dataset published between publish_datetime_from and publish_datetime_to.
        Automatically chunks requests longer than 10 days to ensure fast and reliable streaming.
        Cached by publish datetime range.
        """
        cache_key = f"{publish_datetime_from}_{publish_datetime_to}"
        if cache_key in self._windfor_cache:
            return self._windfor_cache[cache_key]

        start_dt = parse_utc_iso(publish_datetime_from)
        end_dt = parse_utc_iso(publish_datetime_to)

        forecast_records: List[WindforRecord] = []
        chunk_days = 10
        current_start = start_dt

        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=chunk_days), end_dt)
            chunk_from = current_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            chunk_to = current_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            raw_records = await self._request_with_retry(
                "datasets/WINDFOR/stream",
                params={
                    "publishDateTimeFrom": chunk_from,
                    "publishDateTimeTo": chunk_to,
                },
            )

            for r in raw_records:
                try:
                    forecast_records.append(
                        WindforRecord(
                            dataset=r.get("dataset", "WINDFOR"),
                            publish_time=parse_utc_iso(r["publishTime"]),
                            start_time=parse_utc_iso(r["startTime"]),
                            generation=int(r.get("generation", 0)),
                        )
                    )
                except (KeyError, ValueError, TypeError) as ex:
                    logger.debug("Skipping malformed WINDFOR record %s: %s", r, ex)

            current_start = current_end

        self._windfor_cache[cache_key] = forecast_records
        return forecast_records

    @staticmethod
    def deduplicate_fuelhh(records: List[FuelhhRecord]) -> List[FuelhhRecord]:
        """
        Deduplicate FUELHH records by startTime:
        If multiple records exist for the same startTime (due to republication or
        data revisions), select the record with the latest publishTime.
        """
        records_by_time: Dict[datetime, FuelhhRecord] = {}
        for rec in records:
            existing = records_by_time.get(rec.start_time)
            if existing is None or rec.publish_time > existing.publish_time:
                records_by_time[rec.start_time] = rec
        return list(records_by_time.values())
