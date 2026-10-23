"""
Shared pytest fixtures and synthetic data builders.
"""

from datetime import datetime, timezone
import pytest
from app.models.domain import FuelhhRecord, WindforRecord


def make_fuelhh(
    start_iso: str,
    generation: int = 1000,
    publish_iso: str = "2026-01-01T00:00:00Z",
    fuel_type: str = "WIND",
    settlement_date: str = "2026-01-01",
    settlement_period: int = 1,
) -> FuelhhRecord:
    """Helper to create a FuelhhRecord with UTC datetimes."""
    return FuelhhRecord(
        dataset="FUELHH",
        publish_time=datetime.fromisoformat(publish_iso.replace("Z", "+00:00")),
        start_time=datetime.fromisoformat(start_iso.replace("Z", "+00:00")),
        settlement_date=settlement_date,
        settlement_period=settlement_period,
        fuel_type=fuel_type,
        generation=generation,
    )


def make_windfor(
    start_iso: str,
    generation: int = 1200,
    publish_iso: str = "2026-01-01T07:00:00Z",
) -> WindforRecord:
    """Helper to create a WindforRecord with UTC datetimes."""
    return WindforRecord(
        dataset="WINDFOR",
        publish_time=datetime.fromisoformat(publish_iso.replace("Z", "+00:00")),
        start_time=datetime.fromisoformat(start_iso.replace("Z", "+00:00")),
        generation=generation,
    )
