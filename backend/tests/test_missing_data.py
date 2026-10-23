"""
Tests for missing and edge-case data handling.
"""

from datetime import datetime, timezone
import pytest
from app.models.domain import EligibleForecast, HourlyActual
from app.services.aggregation import aggregate_fuelhh_to_hourly
from app.services.analysis_service import match_and_analyze
from tests.conftest import make_fuelhh, make_windfor


def test_gap_in_fuelhh_hours_are_missing():
    # Only hours 00:00 and 03:00 present. Hours 01:00 and 02:00 missing.
    target_hours = [
        datetime(2026, 1, 2, h, 0, tzinfo=timezone.utc) for h in range(4)
    ]
    records = [
        make_fuelhh("2026-01-02T00:00:00Z", generation=1000),
        make_fuelhh("2026-01-02T00:30:00Z", generation=1000),
        make_fuelhh("2026-01-02T03:00:00Z", generation=1500),
        make_fuelhh("2026-01-02T03:30:00Z", generation=1500),
    ]

    result = aggregate_fuelhh_to_hourly(records, delivery_hours=target_hours)
    assert len(result) == 4
    assert result[0].is_missing is False
    assert result[1].is_missing is True
    assert result[1].generation is None
    assert result[2].is_missing is True
    assert result[3].is_missing is False


def test_entirely_empty_fuelhh_response():
    target_hours = [
        datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    ]
    forecast_map = {
        target_hours[0]: EligibleForecast(
            start_time=target_hours[0],
            publish_time=target_hours[0],
            generation=1200.0,
        )
    }

    actuals = aggregate_fuelhh_to_hourly([], delivery_hours=target_hours)
    actual_map = {a.start_time: a for a in actuals}

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=target_hours,
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert quality.total_delivery_hours == 1
    assert quality.matched_intervals == 0
    assert quality.missing_actual_intervals == 1
    assert metrics.mae is None


def test_entirely_empty_windfor_response():
    target_hours = [
        datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    ]
    actuals = [
        HourlyActual(
            start_time=target_hours[0],
            generation=1000.0,
            is_partial=False,
            is_missing=False,
        )
    ]
    actual_map = {a.start_time: a for a in actuals}
    forecast_map = {target_hours[0]: None}

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=target_hours,
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert quality.matched_intervals == 0
    assert quality.missing_forecast_intervals == 1
    assert metrics.mae is None


def test_actual_zero_mw_preserved_not_missing():
    target_hours = [datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)]
    records = [
        make_fuelhh("2026-01-02T00:00:00Z", generation=0),
        make_fuelhh("2026-01-02T00:30:00Z", generation=0),
    ]

    actuals = aggregate_fuelhh_to_hourly(records, delivery_hours=target_hours)
    assert len(actuals) == 1
    assert actuals[0].generation == 0.0
    assert actuals[0].is_missing is False
