"""
Wind Intelligence — Pydantic request/response schemas.

These models define the API contract between backend and frontend.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case to camelCase for JSON serialization."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HourlyComparisonSchema(CamelModel):
    start_time: str
    forecast_generation: Optional[float] = None
    forecast_publish_time: Optional[str] = None
    forecast_publication_cycle: Optional[str] = None
    actual_generation: Optional[float] = None
    is_partial_actual: bool = False
    is_missing_actual: bool = False
    is_missing_forecast: bool = False
    absolute_error: Optional[float] = None
    signed_error: Optional[float] = None


class AccuracyMetricsSchema(CamelModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mean_bias: Optional[float] = None
    wape: Optional[float] = None
    mape: Optional[float] = None
    mape_excluded_count: int = 0


class DataQualitySchema(CamelModel):
    total_delivery_hours: int
    matched_intervals: int
    missing_forecast_intervals: int
    missing_actual_intervals: int
    partial_actual_intervals: int


class AnalysisConfigSchema(CamelModel):
    decision_cutoff_hour: int
    decision_cutoff_minute: int
    decision_lead_days: int
    analysis_year: int
    analysis_month: int
    elexon_base_url: str


class AnalysisResponseSchema(CamelModel):
    config: AnalysisConfigSchema
    metrics: AccuracyMetricsSchema
    data_quality: DataQualitySchema
    intervals: List[HourlyComparisonSchema]
