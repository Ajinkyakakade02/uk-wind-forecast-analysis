"""
Wind Intelligence — Domain data models.

Dataclasses and type definitions shared across services.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class FuelhhRecord:
    """Raw FUELHH response record from Elexon API."""
    dataset: str
    publish_time: datetime
    start_time: datetime
    settlement_date: str
    settlement_period: int
    fuel_type: str
    generation: int


@dataclass(frozen=True)
class WindforRecord:
    """Raw WINDFOR response record from Elexon API."""
    dataset: str
    publish_time: datetime
    start_time: datetime
    generation: int


@dataclass(frozen=True)
class HourlyActual:
    """Aggregated hourly actual generation."""
    start_time: datetime
    generation: Optional[float]
    is_partial: bool
    is_missing: bool


@dataclass(frozen=True)
class EligibleForecast:
    """Selected forecast for a delivery interval."""
    start_time: datetime
    publish_time: datetime
    generation: float
    publication_cycle: Optional[datetime] = None


@dataclass(frozen=True)
class HourlyComparison:
    """Paired forecast + actual for a single hour."""
    start_time: datetime
    forecast_generation: Optional[float]
    forecast_publish_time: Optional[datetime]
    actual_generation: Optional[float]
    is_partial_actual: bool
    is_missing_actual: bool
    is_missing_forecast: bool
    absolute_error: Optional[float]
    signed_error: Optional[float]
    forecast_publication_cycle: Optional[datetime] = None


@dataclass(frozen=True)
class AccuracyMetrics:
    """Statistical accuracy metrics comparing forecast vs actual."""
    mae: Optional[float]  # Mean Absolute Error (MW)
    rmse: Optional[float]  # Root Mean Square Error (MW)
    mean_bias: Optional[float]  # Mean Bias (MW; + = over-forecast)
    wape: Optional[float]  # Weighted Absolute Percentage Error (%)
    mape: Optional[float] = None  # Mean Absolute Percentage Error (%; actual > 0)
    mape_excluded_count: int = 0  # Number of intervals excluded from MAPE (actual == 0)


@dataclass(frozen=True)
class DataQualitySummary:
    """Summary of data coverage and quality counts."""
    total_delivery_hours: int
    matched_intervals: int
    missing_forecast_intervals: int
    missing_actual_intervals: int
    partial_actual_intervals: int
