"""
Tests for accuracy metric calculations.
"""

from datetime import datetime, timezone
import pytest
from app.models.domain import EligibleForecast, HourlyActual
from app.services.analysis_service import compute_accuracy_metrics, match_and_analyze


def test_mae_known_inputs():
    # pairs: (forecast, actual)
    # (100, 80) -> error 20
    # (200, 250) -> error 50
    # (300, 300) -> error 0
    # MAE = (20 + 50 + 0) / 3 = 70 / 3 = 23.33
    metrics = compute_accuracy_metrics([(100.0, 80.0), (200.0, 250.0), (300.0, 300.0)])
    assert metrics.mae == 23.33


def test_rmse_known_inputs():
    # errors: 3, 4 -> sum squares = 9 + 16 = 25 -> mean = 12.5 -> sqrt = 3.54
    metrics = compute_accuracy_metrics([(13.0, 10.0), (14.0, 10.0)])
    assert metrics.rmse == 3.54


def test_mean_bias():
    # Over-forecast: forecast > actual -> positive bias
    metrics_over = compute_accuracy_metrics([(120.0, 100.0), (150.0, 130.0)])
    assert metrics_over.mean_bias > 0
    assert metrics_over.mean_bias == 20.0

    # Under-forecast: forecast < actual -> negative bias
    metrics_under = compute_accuracy_metrics([(80.0, 100.0), (110.0, 130.0)])
    assert metrics_under.mean_bias < 0
    assert metrics_under.mean_bias == -20.0


def test_wape_calculation():
    # pairs: (120, 100), (80, 100)
    # errors: 20 + 20 = 40
    # sum actuals: 100 + 100 = 200
    # WAPE: 40 / 200 = 20.0%
    metrics = compute_accuracy_metrics([(120.0, 100.0), (80.0, 100.0)])
    assert metrics.wape == 20.0


def test_wape_all_zero_actuals():
    # If sum(actuals) == 0, WAPE is None without crashing
    metrics = compute_accuracy_metrics([(100.0, 0.0), (50.0, 0.0)])
    assert metrics.wape is None


def test_mape_excludes_zero_actuals():
    # pair 1: actual = 0 (should be excluded)
    # pair 2: forecast=110, actual=100 -> error=10, 10/100 = 10%
    metrics = compute_accuracy_metrics([(50.0, 0.0), (110.0, 100.0)])
    assert metrics.mape == 10.0
    assert metrics.mape_excluded_count == 1


def test_empty_input_returns_none():
    metrics = compute_accuracy_metrics([])
    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.mean_bias is None
    assert metrics.wape is None
    assert metrics.mape is None


def test_data_quality_counts_and_partial_exclusion():
    t1 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 1, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 2, 2, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 1, 2, 3, 0, tzinfo=timezone.utc)

    # t1: matched normal
    # t2: matched but partial actual
    # t3: missing forecast (actual exists)
    # t4: missing actual (forecast exists)
    forecast_map = {
        t1: EligibleForecast(start_time=t1, publish_time=t1, generation=1000.0),
        t2: EligibleForecast(start_time=t2, publish_time=t2, generation=2000.0),
        t3: None,
        t4: EligibleForecast(start_time=t4, publish_time=t4, generation=4000.0),
    }

    actual_map = {
        t1: HourlyActual(start_time=t1, generation=1000.0, is_partial=False, is_missing=False),
        t2: HourlyActual(start_time=t2, generation=1500.0, is_partial=True, is_missing=False),
        t3: HourlyActual(start_time=t3, generation=3000.0, is_partial=False, is_missing=False),
        t4: HourlyActual(start_time=t4, generation=None, is_partial=False, is_missing=True),
    }

    # Default: partial excluded from primary metrics
    comparisons, metrics, quality = match_and_analyze(
        delivery_hours=[t1, t2, t3, t4],
        forecast_map=forecast_map,
        actual_map=actual_map,
        include_partial=False,
    )

    assert quality.total_delivery_hours == 4
    assert quality.matched_intervals == 2
    assert quality.missing_forecast_intervals == 1
    assert quality.missing_actual_intervals == 1
    assert quality.partial_actual_intervals == 1

    # In metrics, only t1 is included (error=0) because t2 was partial and excluded
    assert metrics.mae == 0.0

    # If include_partial=True, t2 (error=500) is included -> MAE = (0 + 500) / 2 = 250.0
    _, metrics_with_partial, _ = match_and_analyze(
        delivery_hours=[t1, t2, t3, t4],
        forecast_map=forecast_map,
        actual_map=actual_map,
        include_partial=True,
    )
    assert metrics_with_partial.mae == 250.0
