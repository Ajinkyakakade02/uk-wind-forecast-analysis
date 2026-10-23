"""
Tests for forecast-to-actual interval matching.
"""

from datetime import datetime, timezone
import pytest
from app.models.domain import EligibleForecast, HourlyActual
from app.services.analysis_service import match_and_analyze


def test_forecast_and_actual_matched_correctly():
    t1 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 1, 0, tzinfo=timezone.utc)

    forecast_map = {
        t1: EligibleForecast(start_time=t1, publish_time=t1, generation=1200.0),
        t2: EligibleForecast(start_time=t2, publish_time=t2, generation=1400.0),
    }

    actual_map = {
        t1: HourlyActual(start_time=t1, generation=1000.0, is_partial=False, is_missing=False),
        t2: HourlyActual(start_time=t2, generation=1500.0, is_partial=False, is_missing=False),
    }

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=[t1, t2],
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert len(comparisons) == 2
    assert comparisons[0].start_time == t1
    assert comparisons[0].forecast_generation == 1200.0
    assert comparisons[0].actual_generation == 1000.0
    assert comparisons[0].absolute_error == 200.0
    assert comparisons[0].signed_error == 200.0

    assert comparisons[1].absolute_error == 100.0
    assert comparisons[1].signed_error == -100.0
    assert quality.matched_intervals == 2


def test_missing_actual_counted_and_excluded_from_metrics():
    t1 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    forecast_map = {
        t1: EligibleForecast(start_time=t1, publish_time=t1, generation=1200.0),
    }
    actual_map = {
        t1: HourlyActual(start_time=t1, generation=None, is_partial=False, is_missing=True),
    }

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=[t1],
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert quality.matched_intervals == 0
    assert quality.missing_actual_intervals == 1
    assert metrics.mae is None


def test_missing_forecast_counted_and_excluded_from_metrics():
    t1 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    forecast_map = {t1: None}
    actual_map = {
        t1: HourlyActual(start_time=t1, generation=1000.0, is_partial=False, is_missing=False),
    }

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=[t1],
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert quality.matched_intervals == 0
    assert quality.missing_forecast_intervals == 1
    assert metrics.mae is None


def test_multiple_dates_joined_independently():
    d1 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    d2 = datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc)

    forecast_map = {
        d1: EligibleForecast(start_time=d1, publish_time=d1, generation=1000.0),
        d2: EligibleForecast(start_time=d2, publish_time=d2, generation=2000.0),
    }
    actual_map = {
        d1: HourlyActual(start_time=d1, generation=1000.0, is_partial=False, is_missing=False),
        d2: HourlyActual(start_time=d2, generation=2500.0, is_partial=False, is_missing=False),
    }

    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=[d1, d2],
        forecast_map=forecast_map,
        actual_map=actual_map,
    )

    assert quality.matched_intervals == 2
    assert metrics.mae == 250.0
