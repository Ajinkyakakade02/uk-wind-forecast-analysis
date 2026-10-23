"""
Wind Intelligence — Forecast selection service.

Selects the best-available wind forecast for each delivery interval
based on a configurable decision cutoff.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from app.models.domain import EligibleForecast, WindforRecord


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_publication_cycle(pub_dt: datetime) -> datetime:
    """
    Map an Elexon raw record publishTime to its official NGESO scheduled publication cycle.

    NGESO publishes updates up to 8 times a day at scheduled milestones:
        03:30, 05:30, 08:30, 10:30, 12:30, 16:30, 19:30, 23:30 UTC.
    In Elexon's raw BMRS database, records are stamped with internal model/creation timestamps
    (typically 02:30, 04:30, 07:30, 09:30, 11:30 or 12:25, 15:30, 18:30, 22:30 UTC).

    This function determines the verified market availability milestone (publication cycle)
    while preserving the raw source timestamp for traceability.
    """
    pub_utc = ensure_utc(pub_dt)
    h = pub_utc.hour
    d = pub_utc.date()

    if 2 <= h < 4:
        cycle_t = time(3, 30)
    elif 4 <= h < 6:
        cycle_t = time(5, 30)
    elif 7 <= h < 9:
        cycle_t = time(8, 30)
    elif 9 <= h < 11:
        cycle_t = time(10, 30)
    elif 11 <= h < 14:
        cycle_t = time(12, 30)
    elif 15 <= h < 17:
        cycle_t = time(16, 30)
    elif 18 <= h < 20:
        cycle_t = time(19, 30)
    elif 22 <= h <= 23:
        cycle_t = time(23, 30)
    else:
        # Fallback to the timestamp itself if an unexpected ad-hoc run occurs
        return pub_utc

    return datetime.combine(d, cycle_t, tzinfo=timezone.utc)


def select_forecast_for_interval(
    delivery_interval: datetime,
    cutoff: datetime,
    records: Iterable[WindforRecord],
    use_publication_cycle: bool = True,
) -> Optional[EligibleForecast]:
    """
    Select the eligible forecast for a delivery interval:
        1. Gather all WINDFOR records whose startTime matches delivery_interval.
        2. Filter to records whose effective publication time is strictly < cutoff.
           - When use_publication_cycle=False (default): effective publication time is
             the record's raw publishTime (matching Elexon API database queries).
           - When use_publication_cycle=True: effective publication time is the official
             scheduled NGESO publication milestone (e.g. 08:30 for the 07:30 raw run).
        3. From eligible records, select the one with the latest publication time.
        4. If no eligible forecast exists, return None.
    """
    delivery_utc = ensure_utc(delivery_interval)
    cutoff_utc = ensure_utc(cutoff)

    best_record: Optional[WindforRecord] = None
    best_eff_time: Optional[datetime] = None

    for rec in records:
        rec_start_utc = ensure_utc(rec.start_time)
        if rec_start_utc != delivery_utc:
            continue

        rec_pub_utc = ensure_utc(rec.publish_time)
        eff_pub_utc = (
            get_publication_cycle(rec_pub_utc) if use_publication_cycle else rec_pub_utc
        )

        # Strict inequality: effective publication time strictly < cutoff
        if eff_pub_utc < cutoff_utc:
            if best_record is None or best_eff_time is None or eff_pub_utc > best_eff_time:
                best_record = rec
                best_eff_time = eff_pub_utc
            elif eff_pub_utc == best_eff_time:
                # If same effective cycle, pick latest raw publish time
                if rec_pub_utc > ensure_utc(best_record.publish_time):
                    best_record = rec
                    best_eff_time = eff_pub_utc

    if best_record is not None:
        rec_pub_utc = ensure_utc(best_record.publish_time)
        return EligibleForecast(
            start_time=delivery_utc,
            publish_time=rec_pub_utc,
            generation=float(best_record.generation),
            publication_cycle=get_publication_cycle(rec_pub_utc),
        )
    return None


def select_forecasts_for_window(
    decision_dates: Iterable[date],
    cutoff_hour: int,
    cutoff_minute: int,
    lead_days: int,
    records: Iterable[WindforRecord],
    use_publication_cycle: bool = True,
) -> Dict[datetime, Optional[EligibleForecast]]:
    """
    For a sequence of decision dates, evaluate each 24 delivery hours:
        delivery_date = decision_date + timedelta(days=lead_days)
        cutoff = datetime(decision_date, cutoff_hour, cutoff_minute, UTC)
    Returns a dict mapping delivery_interval (hour start UTC) -> EligibleForecast or None.
    """
    results: Dict[datetime, Optional[EligibleForecast]] = {}
    record_list = list(records)

    for d_date in decision_dates:
        cutoff_dt = datetime.combine(
            d_date, time(hour=cutoff_hour, minute=cutoff_minute), tzinfo=timezone.utc
        )
        delivery_date = d_date + timedelta(days=lead_days)

        for hour in range(24):
            delivery_interval = datetime.combine(
                delivery_date, time(hour=hour, minute=0), tzinfo=timezone.utc
            )
            forecast = select_forecast_for_interval(
                delivery_interval=delivery_interval,
                cutoff=cutoff_dt,
                records=record_list,
                use_publication_cycle=use_publication_cycle,
            )
            results[delivery_interval] = forecast

    return results
