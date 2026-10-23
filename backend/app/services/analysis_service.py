"""
Wind Intelligence — Forecast accuracy analysis service.

Computes accuracy metrics comparing selected wind forecasts
against aggregated actual generation.
"""

from datetime import datetime, timezone
import math
from typing import Dict, Iterable, List, Optional, Tuple
from app.models.domain import (
    AccuracyMetrics,
    DataQualitySummary,
    EligibleForecast,
    HourlyActual,
    HourlyComparison,
)


def compute_accuracy_metrics(
    pairs: Iterable[Tuple[float, float]],
    zero_actual_count: int = 0,
) -> AccuracyMetrics:
    """
    Compute accuracy metrics from an iterable of (forecast, actual) pairs.
    If pairs is empty, all metrics return None.
    """
    pair_list = list(pairs)
    n = len(pair_list)

    if n == 0:
        return AccuracyMetrics(
            mae=None,
            rmse=None,
            mean_bias=None,
            wape=None,
            mape=None,
            mape_excluded_count=zero_actual_count,
        )

    abs_errors = [abs(f - a) for f, a in pair_list]
    squared_errors = [(f - a) ** 2 for f, a in pair_list]
    signed_errors = [f - a for f, a in pair_list]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(squared_errors) / n)
    mean_bias = sum(signed_errors) / n

    total_actual = sum(abs(a) for _, a in pair_list)
    if total_actual > 0:
        wape = (sum(abs_errors) / total_actual) * 100.0
    else:
        wape = None

    # MAPE: compute over pairs where actual > 0
    mape_pairs = [(f, a) for f, a in pair_list if a > 0]
    excluded_for_mape = zero_actual_count + sum(1 for _, a in pair_list if a == 0)

    if len(mape_pairs) > 0:
        mape = (sum(abs(f - a) / a for f, a in mape_pairs) / len(mape_pairs)) * 100.0
    else:
        mape = None

    return AccuracyMetrics(
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        mean_bias=round(mean_bias, 2),
        wape=round(wape, 2) if wape is not None else None,
        mape=round(mape, 2) if mape is not None else None,
        mape_excluded_count=excluded_for_mape,
    )


def match_and_analyze(
    delivery_hours: Iterable[datetime],
    forecast_map: Dict[datetime, Optional[EligibleForecast]],
    actual_map: Dict[datetime, Optional[HourlyActual]],
    include_partial: bool = False,
) -> Tuple[List[HourlyComparison], AccuracyMetrics, DataQualitySummary]:
    """
    Compare forecasts against actuals across all delivery hours.
    Returns:
        1. List of HourlyComparison objects for each hour.
        2. Computed AccuracyMetrics.
        3. DataQualitySummary.
    """
    sorted_hours = sorted(delivery_hours)
    comparisons: List[HourlyComparison] = []

    metric_eval_pairs: List[Tuple[float, float]] = []
    zero_actuals_excluded = 0

    matched_count = 0
    missing_forecast_count = 0
    missing_actual_count = 0
    partial_actual_count = 0

    for hour in sorted_hours:
        hour_utc = hour if hour.tzinfo is not None else hour.replace(tzinfo=timezone.utc)
        fc = forecast_map.get(hour_utc)
        act = actual_map.get(hour_utc)

        forecast_val = fc.generation if fc is not None else None
        forecast_pub = fc.publish_time if fc is not None else None
        forecast_cycle = fc.publication_cycle if fc is not None else None

        actual_val = act.generation if act is not None and not act.is_missing else None
        is_partial = act.is_partial if act is not None else False
        is_missing_actual = (act is None) or act.is_missing or (actual_val is None)
        is_missing_forecast = forecast_val is None

        if is_partial:
            partial_actual_count += 1

        if not is_missing_forecast and not is_missing_actual:
            matched_count += 1
            abs_err = abs(forecast_val - actual_val)
            signed_err = forecast_val - actual_val

            # By default, exclude partial actuals from primary metrics
            if not is_partial or include_partial:
                metric_eval_pairs.append((forecast_val, actual_val))
        elif is_missing_forecast and not is_missing_actual:
            missing_forecast_count += 1
            abs_err = None
            signed_err = None
        elif not is_missing_forecast and is_missing_actual:
            missing_actual_count += 1
            abs_err = None
            signed_err = None
        else:
            abs_err = None
            signed_err = None

        comparisons.append(
            HourlyComparison(
                start_time=hour_utc,
                forecast_generation=forecast_val,
                forecast_publish_time=forecast_pub,
                forecast_publication_cycle=forecast_cycle,
                actual_generation=actual_val,
                is_partial_actual=is_partial,
                is_missing_actual=is_missing_actual,
                is_missing_forecast=is_missing_forecast,
                absolute_error=round(abs_err, 2) if abs_err is not None else None,
                signed_error=round(signed_err, 2) if signed_err is not None else None,
            )
        )

    metrics = compute_accuracy_metrics(metric_eval_pairs, zero_actual_count=zero_actuals_excluded)

    data_quality = DataQualitySummary(
        total_delivery_hours=len(sorted_hours),
        matched_intervals=matched_count,
        missing_forecast_intervals=missing_forecast_count,
        missing_actual_intervals=missing_actual_count,
        partial_actual_intervals=partial_actual_count,
    )

    return comparisons, metrics, data_quality
