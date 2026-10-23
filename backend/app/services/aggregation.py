"""
Wind Intelligence — Half-hourly to hourly aggregation.

Aggregates FUELHH half-hourly actual generation data into hourly
values for comparison with hourly WINDFOR forecasts.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from app.models.domain import FuelhhRecord, HourlyActual
from app.services.elexon_client import ElexonClient


def deduplicate_fuelhh(records: Iterable[FuelhhRecord]) -> Dict[datetime, FuelhhRecord]:
    """
    Select the record with the latest publishTime for any duplicated startTime.
    Returns a dictionary mapping startTime -> FuelhhRecord.
    """
    deduped: Dict[datetime, FuelhhRecord] = {}
    for rec in records:
        existing = deduped.get(rec.start_time)
        if existing is None or rec.publish_time > existing.publish_time:
            deduped[rec.start_time] = rec
    return deduped


def aggregate_fuelhh_to_hourly(
    records: Iterable[FuelhhRecord],
    delivery_hours: Optional[Iterable[datetime]] = None,
) -> List[HourlyActual]:
    """
    Aggregate half-hourly FUELHH wind actuals to hourly intervals.

    Rules for each delivery hour H:
        - Both H:00 and H:30 present  → hourly_actual = mean(H:00, H:30); partial=False
        - Only H:00 present           → hourly_actual = H:00 value;     partial=True
        - Only H:30 present           → hourly_actual = H:30 value;     partial=True
        - Neither present             → hourly_actual = None;           missing=True

    Zero generation (0 MW) is preserved as a genuine value, not treated as missing.
    """
    # 1. Deduplicate by startTime selecting latest publishTime
    record_map = deduplicate_fuelhh(records)

    # 2. Determine target delivery hours
    if delivery_hours is not None:
        target_hours = sorted(delivery_hours)
    else:
        # Infer target hours from records: all distinct hour boundaries
        hour_set = set()
        for st in record_map.keys():
            hour_aligned = st.replace(minute=0, second=0, microsecond=0)
            hour_set.add(hour_aligned)
        target_hours = sorted(hour_set)

    hourly_actuals: List[HourlyActual] = []

    for hour_start in target_hours:
        # Guarantee hour alignment & UTC
        if hour_start.tzinfo is None:
            h00_time = hour_start.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        else:
            h00_time = hour_start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)

        h30_time = h00_time + timedelta(minutes=30)

        rec_00 = record_map.get(h00_time)
        rec_30 = record_map.get(h30_time)

        if rec_00 is not None and rec_30 is not None:
            avg_gen = (float(rec_00.generation) + float(rec_30.generation)) / 2.0
            hourly_actuals.append(
                HourlyActual(
                    start_time=h00_time,
                    generation=avg_gen,
                    is_partial=False,
                    is_missing=False,
                )
            )
        elif rec_00 is not None:
            hourly_actuals.append(
                HourlyActual(
                    start_time=h00_time,
                    generation=float(rec_00.generation),
                    is_partial=True,
                    is_missing=False,
                )
            )
        elif rec_30 is not None:
            hourly_actuals.append(
                HourlyActual(
                    start_time=h00_time,
                    generation=float(rec_30.generation),
                    is_partial=True,
                    is_missing=False,
                )
            )
        else:
            hourly_actuals.append(
                HourlyActual(
                    start_time=h00_time,
                    generation=None,
                    is_partial=False,
                    is_missing=True,
                )
            )

    return hourly_actuals
