"""
Tests for half-hourly to hourly aggregation.
"""

from datetime import datetime, timezone
import pytest
from app.services.aggregation import aggregate_fuelhh_to_hourly, deduplicate_fuelhh
from tests.conftest import make_fuelhh


def test_both_present_averages_correctly():
    rec_00 = make_fuelhh("2026-01-01T10:00:00Z", generation=1000)
    rec_30 = make_fuelhh("2026-01-01T10:30:00Z", generation=2000)

    result = aggregate_fuelhh_to_hourly([rec_00, rec_30])
    assert len(result) == 1
    assert result[0].generation == 1500.0
    assert result[0].is_partial is False
    assert result[0].is_missing is False
    assert result[0].start_time == datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def test_only_00_present_is_partial():
    rec_00 = make_fuelhh("2026-01-01T10:00:00Z", generation=1200)

    result = aggregate_fuelhh_to_hourly([rec_00])
    assert len(result) == 1
    assert result[0].generation == 1200.0
    assert result[0].is_partial is True
    assert result[0].is_missing is False


def test_only_30_present_is_partial():
    rec_30 = make_fuelhh("2026-01-01T10:30:00Z", generation=1400)

    result = aggregate_fuelhh_to_hourly([rec_30])
    assert len(result) == 1
    assert result[0].generation == 1400.0
    assert result[0].is_partial is True
    assert result[0].is_missing is False
    assert result[0].start_time.minute == 0


def test_neither_present_is_missing():
    target_hour = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    result = aggregate_fuelhh_to_hourly([], delivery_hours=[target_hour])

    assert len(result) == 1
    assert result[0].generation is None
    assert result[0].is_missing is True
    assert result[0].is_partial is False


def test_full_day_48_records_yields_24_hours():
    records = []
    for h in range(24):
        records.append(make_fuelhh(f"2026-01-01T{h:02d}:00:00Z", generation=1000 + h))
        records.append(make_fuelhh(f"2026-01-01T{h:02d}:30:00Z", generation=2000 + h))

    result = aggregate_fuelhh_to_hourly(records)
    assert len(result) == 24
    assert all(r.is_partial is False for r in result)
    assert all(r.is_missing is False for r in result)


def test_deduplication_latest_publish_wins():
    rec_early = make_fuelhh(
        "2026-01-01T10:00:00Z",
        generation=1000,
        publish_iso="2026-01-01T11:00:00Z",
    )
    rec_revised = make_fuelhh(
        "2026-01-01T10:00:00Z",
        generation=1500,
        publish_iso="2026-01-01T12:00:00Z",  # Later publish time
    )

    rec_30 = make_fuelhh(
        "2026-01-01T10:30:00Z",
        generation=1500,
        publish_iso="2026-01-01T11:00:00Z",
    )

    result = aggregate_fuelhh_to_hourly([rec_early, rec_revised, rec_30])
    assert len(result) == 1
    # Average of 1500 (revised) and 1500 = 1500.0
    assert result[0].generation == 1500.0


def test_zero_generation_preserved_not_missing():
    rec_00 = make_fuelhh("2026-01-01T10:00:00Z", generation=0)
    rec_30 = make_fuelhh("2026-01-01T10:30:00Z", generation=0)

    result = aggregate_fuelhh_to_hourly([rec_00, rec_30])
    assert len(result) == 1
    assert result[0].generation == 0.0
    assert result[0].is_missing is False
