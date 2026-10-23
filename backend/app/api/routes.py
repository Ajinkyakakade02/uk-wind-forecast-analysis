"""
Wind Intelligence — API route handlers.

Thin layer: validates request parameters, delegates to services,
returns Pydantic response models. No business logic here.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    AccuracyMetricsSchema,
    AnalysisConfigSchema,
    AnalysisResponseSchema,
    DataQualitySchema,
    HourlyComparisonSchema,
)
from app.config import Settings, get_settings
from app.services.aggregation import aggregate_fuelhh_to_hourly
from app.services.analysis_service import match_and_analyze
from app.services.elexon_client import ElexonClient
from app.services.forecast_service import select_forecasts_for_window

router = APIRouter()

# Shared singleton client for caching
_elexon_client: Optional[ElexonClient] = None


def get_elexon_client(settings: Settings = Depends(get_settings)) -> ElexonClient:
    global _elexon_client
    if _elexon_client is None:
        _elexon_client = ElexonClient(settings=settings)
    return _elexon_client


@router.get("/config", response_model=AnalysisConfigSchema, response_model_by_alias=True)
async def get_config(settings: Settings = Depends(get_settings)):
    """Return current analysis configuration."""
    return AnalysisConfigSchema(
        decision_cutoff_hour=settings.decision_cutoff_hour,
        decision_cutoff_minute=settings.decision_cutoff_minute,
        decision_lead_days=settings.decision_lead_days,
        analysis_year=settings.analysis_year,
        analysis_month=settings.analysis_month,
        elexon_base_url=settings.elexon_base_url,
    )


@router.get("/analysis", response_model=AnalysisResponseSchema, response_model_by_alias=True)
async def get_analysis(
    cutoff_hour: Optional[int] = Query(None, ge=0, le=23, description="Decision cutoff hour (UTC)"),
    start_date: Optional[str] = Query(None, description="Start decision date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End decision date (YYYY-MM-DD)"),
    include_partial: bool = Query(False, description="Include partial half-hour actuals in metrics"),
    settings: Settings = Depends(get_settings),
    client: ElexonClient = Depends(get_elexon_client),
):
    """
    Return forecast accuracy analysis for the specified decision window.
    """
    effective_cutoff_hour = (
        cutoff_hour if cutoff_hour is not None else settings.decision_cutoff_hour
    )
    effective_cutoff_min = settings.decision_cutoff_minute
    lead_days = settings.decision_lead_days

    # Determine date range
    try:
        if start_date:
            d_start = date.fromisoformat(start_date)
        else:
            d_start = date(settings.analysis_year, settings.analysis_month, 1)

        if end_date:
            d_end = date.fromisoformat(end_date)
        else:
            _, last_day = calendar.monthrange(settings.analysis_year, settings.analysis_month)
            d_end = date(settings.analysis_year, settings.analysis_month, last_day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if d_start > d_end:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    # Generate sequence of decision dates
    curr = d_start
    decision_dates: List[date] = []
    while curr <= d_end:
        decision_dates.append(curr)
        curr += timedelta(days=1)

    # Delivery dates
    delivery_dates = [d + timedelta(days=lead_days) for d in decision_dates]
    first_delivery = min(delivery_dates)
    last_delivery = max(delivery_dates)

    # Fetch datasets
    fuelhh_records = await client.fetch_fuelhh_wind(
        settlement_date_from=first_delivery.strftime("%Y-%m-%d"),
        settlement_date_to=last_delivery.strftime("%Y-%m-%d"),
    )

    # Fetch WINDFOR forecasts published in the relevant window
    earliest_pub = (min(decision_dates) - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")
    latest_pub = (max(decision_dates) + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59Z")
    windfor_records = await client.fetch_windfor(
        publish_datetime_from=earliest_pub,
        publish_datetime_to=latest_pub,
    )

    # Select forecasts
    forecast_map = select_forecasts_for_window(
        decision_dates=decision_dates,
        cutoff_hour=effective_cutoff_hour,
        cutoff_minute=effective_cutoff_min,
        lead_days=lead_days,
        records=windfor_records,
    )

    # Aggregate actuals
    delivery_hours = sorted(forecast_map.keys())
    actual_list = aggregate_fuelhh_to_hourly(fuelhh_records, delivery_hours=delivery_hours)
    actual_map = {a.start_time: a for a in actual_list}

    # Match and analyze
    comparisons, metrics, data_quality = match_and_analyze(
        delivery_hours=delivery_hours,
        forecast_map=forecast_map,
        actual_map=actual_map,
        include_partial=include_partial,
    )

    # Map to schema models
    intervals_schema = [
        HourlyComparisonSchema(
            start_time=c.start_time.isoformat(),
            forecast_generation=c.forecast_generation,
            forecast_publish_time=c.forecast_publish_time.isoformat()
            if c.forecast_publish_time
            else None,
            forecast_publication_cycle=c.forecast_publication_cycle.isoformat()
            if c.forecast_publication_cycle
            else None,
            actual_generation=c.actual_generation,
            is_partial_actual=c.is_partial_actual,
            is_missing_actual=c.is_missing_actual,
            is_missing_forecast=c.is_missing_forecast,
            absolute_error=c.absolute_error,
            signed_error=c.signed_error,
        )
        for c in comparisons
    ]

    metrics_schema = AccuracyMetricsSchema(
        mae=metrics.mae,
        rmse=metrics.rmse,
        mean_bias=metrics.mean_bias,
        wape=metrics.wape,
        mape=metrics.mape,
        mape_excluded_count=metrics.mape_excluded_count,
    )

    quality_schema = DataQualitySchema(
        total_delivery_hours=data_quality.total_delivery_hours,
        matched_intervals=data_quality.matched_intervals,
        missing_forecast_intervals=data_quality.missing_forecast_intervals,
        missing_actual_intervals=data_quality.missing_actual_intervals,
        partial_actual_intervals=data_quality.partial_actual_intervals,
    )

    config_schema = AnalysisConfigSchema(
        decision_cutoff_hour=effective_cutoff_hour,
        decision_cutoff_minute=effective_cutoff_min,
        decision_lead_days=lead_days,
        analysis_year=settings.analysis_year,
        analysis_month=settings.analysis_month,
        elexon_base_url=settings.elexon_base_url,
    )

    return AnalysisResponseSchema(
        config=config_schema,
        metrics=metrics_schema,
        data_quality=quality_schema,
        intervals=intervals_schema,
    )
