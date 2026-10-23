"""
Tests for forecast cutoff selection logic.

Covers:
  - Raw timestamp boundary semantics (use_publication_cycle=False)
  - Publication cycle boundary semantics (use_publication_cycle=True, the default)
  - Cutoff hour=8 and hour=9 regressions with realistic Elexon data
  - Window-level selection propagation
"""

from datetime import date, datetime, timezone
import pytest
from app.services.forecast_service import (
    get_publication_cycle,
    select_forecast_for_interval,
    select_forecasts_for_window,
)
from tests.conftest import make_windfor


# ---------------------------------------------------------------------------
# Raw-timestamp mode tests (use_publication_cycle=False)
# ---------------------------------------------------------------------------

def test_raw_mode_forecast_strictly_before_cutoff_selected():
    """Raw-timestamp mode: a record published at 07:59:59 is before an 08:00 cutoff."""
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    rec = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1500,
        publish_iso="2026-01-01T07:59:59Z",
    )

    selected = select_forecast_for_interval(
        delivery, cutoff, [rec], use_publication_cycle=False
    )
    assert selected is not None
    assert selected.generation == 1500.0


def test_raw_mode_forecast_at_exact_cutoff_excluded():
    """Raw-timestamp mode: a record published exactly at cutoff is excluded (strict <)."""
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    rec = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1500,
        publish_iso="2026-01-01T08:00:00Z",
    )

    selected = select_forecast_for_interval(
        delivery, cutoff, [rec], use_publication_cycle=False
    )
    assert selected is None


def test_raw_mode_forecast_after_cutoff_excluded():
    """Raw-timestamp mode: a record published after cutoff is excluded."""
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    rec = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1500,
        publish_iso="2026-01-01T08:00:01Z",
    )

    selected = select_forecast_for_interval(
        delivery, cutoff, [rec], use_publication_cycle=False
    )
    assert selected is None


def test_raw_mode_multiple_eligible_latest_publish_wins():
    """Raw-timestamp mode: from eligible records, pick the latest published."""
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    rec1 = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1000,
        publish_iso="2026-01-01T06:00:00Z",
    )
    rec2 = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1800,
        publish_iso="2026-01-01T07:30:00Z",
    )
    rec3 = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=2500,
        publish_iso="2026-01-01T08:30:00Z",  # After cutoff
    )

    selected = select_forecast_for_interval(
        delivery, cutoff, [rec1, rec2, rec3], use_publication_cycle=False
    )
    assert selected is not None
    assert selected.generation == 1800.0
    assert selected.publish_time == datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc)


def test_raw_mode_no_eligible_returns_none():
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    selected = select_forecast_for_interval(
        delivery, cutoff, [], use_publication_cycle=False
    )
    assert selected is None


def test_raw_mode_configurable_cutoff():
    delivery = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

    rec = make_windfor(
        start_iso="2026-01-02T12:00:00Z",
        generation=1500,
        publish_iso="2026-01-01T10:00:00Z",
    )

    # Cutoff at 08:00 excludes it (raw 10:00 >= 08:00)
    selected_08 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc), [rec],
        use_publication_cycle=False,
    )
    assert selected_08 is None

    # Cutoff at 11:00 includes it (raw 10:00 < 11:00)
    selected_11 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc), [rec],
        use_publication_cycle=False,
    )
    assert selected_11 is not None
    assert selected_11.generation == 1500.0


# ---------------------------------------------------------------------------
# Publication cycle mode tests (default, use_publication_cycle=True)
# ---------------------------------------------------------------------------

def test_cycle_mode_is_default():
    """Verify publication cycle mode is the default (no explicit parameter)."""
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    # Raw 07:30 → cycle 08:30. With cutoff 08:00, cycle 08:30 >= 08:00 → excluded.
    rec_0730 = make_windfor(
        start_iso="2026-01-02T00:00:00Z",
        generation=18781,
        publish_iso="2026-01-01T07:30:00Z",
    )
    # Raw 04:30 → cycle 05:30. With cutoff 08:00, cycle 05:30 < 08:00 → eligible.
    rec_0430 = make_windfor(
        start_iso="2026-01-02T00:00:00Z",
        generation=18719,
        publish_iso="2026-01-01T04:30:00Z",
    )

    # No explicit use_publication_cycle argument — must use cycle semantics by default.
    selected = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
        [rec_0730, rec_0430],
    )
    assert selected is not None
    # Must select 04:30 raw (05:30 cycle), NOT 07:30 raw (08:30 cycle).
    assert selected.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)
    assert selected.publication_cycle == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert selected.generation == 18719.0


def test_cycle_mode_0830_excluded_for_cutoff_08():
    """
    Publication cycle mode: raw 07:30 maps to cycle 08:30.
    With cutoff 08:00, 08:30 >= 08:00 → excluded.
    The 05:30 cycle (raw 04:30) should be selected.
    """
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    cutoff_08 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18767, publish_iso="2026-01-01T02:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18699, publish_iso="2026-01-01T09:30:00Z"),
    ]

    selected = select_forecast_for_interval(delivery, cutoff_08, records)
    assert selected is not None
    assert selected.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)
    assert selected.publication_cycle == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert selected.generation == 18719.0


def test_cycle_mode_0830_included_for_cutoff_09():
    """
    Publication cycle mode: raw 07:30 maps to cycle 08:30.
    With cutoff 09:00, 08:30 < 09:00 → eligible and latest before cutoff.
    """
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    cutoff_09 = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18767, publish_iso="2026-01-01T02:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18699, publish_iso="2026-01-01T09:30:00Z"),
    ]

    selected = select_forecast_for_interval(delivery, cutoff_09, records)
    assert selected is not None
    assert selected.publish_time == datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc)
    assert selected.publication_cycle == datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    assert selected.generation == 18781.0


def test_cycle_mode_exact_boundary_excluded():
    """
    Publication cycle mode: a record whose cycle equals the cutoff exactly is excluded (strict <).
    Cutoff 08:30, cycle 08:30 → excluded.
    """
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    cutoff_0830 = datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
    ]

    selected = select_forecast_for_interval(delivery, cutoff_0830, records)
    assert selected is not None
    # Cycle 08:30 == cutoff 08:30 → excluded. Cycle 05:30 < 08:30 → selected.
    assert selected.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)
    assert selected.publication_cycle == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert selected.generation == 18719.0


def test_cycle_mode_no_eligible_returns_none():
    """Cycle mode: cutoff before the earliest cycle means no eligible forecast."""
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    cutoff_0200 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18767, publish_iso="2026-01-01T02:30:00Z"),
    ]

    selected = select_forecast_for_interval(delivery, cutoff_0200, records)
    assert selected is None


# ---------------------------------------------------------------------------
# Publication cycle mapping function tests
# ---------------------------------------------------------------------------

def test_publication_cycle_mapping():
    """Verify the raw→cycle mapping for all known Elexon publication pairs."""
    test_cases = [
        (datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 3, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 11, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 15, 12, 25, tzinfo=timezone.utc), datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 16, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 18, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 19, 30, tzinfo=timezone.utc)),
        (datetime(2026, 1, 1, 22, 30, tzinfo=timezone.utc), datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc)),
    ]
    for raw, expected_cycle in test_cases:
        actual_cycle = get_publication_cycle(raw)
        assert actual_cycle == expected_cycle, (
            f"Raw {raw.isoformat()} → expected cycle {expected_cycle.isoformat()}, "
            f"got {actual_cycle.isoformat()}"
        )


# ---------------------------------------------------------------------------
# Verified Elexon BMRS regression tests (preserved from original)
# ---------------------------------------------------------------------------

def test_elexon_real_world_publication_schedule_selection():
    """
    Regression test verifying selection against verified Elexon BMRS WINDFOR publication cycles.
    The official NGESO scheduled publication milestones are 03:30, 05:30, 08:30, 10:30 UTC.
    The raw BMRS database records carry internal model timestamps (02:30, 04:30, 07:30, 09:30 UTC).

    Requirements:
        - Under publication cycle semantics, an 08:30 publication cycle (raw 07:30 UTC)
          must be EXCLUDED for an 08:00 UTC cutoff. The latest eligible forecast before
          08:00 UTC is the 05:30 cycle (raw 04:30 UTC).
        - An 08:30 publication cycle (raw 07:30 UTC) may be SELECTED for a 09:00 UTC cutoff
          as the latest eligible forecast.
    """
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18767, publish_iso="2026-01-01T02:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18699, publish_iso="2026-01-01T09:30:00Z"),
    ]

    # CASE 1: 08:00 UTC Cutoff with cycle semantics
    sel_08 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc), records, use_publication_cycle=True
    )
    assert sel_08 is not None
    assert sel_08.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)
    assert sel_08.publication_cycle == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert sel_08.generation == 18719.0

    # CASE 2: 09:00 UTC Cutoff with cycle semantics
    sel_09 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc), records, use_publication_cycle=True
    )
    assert sel_09 is not None
    assert sel_09.publish_time == datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc)
    assert sel_09.publication_cycle == datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    assert sel_09.generation == 18781.0

    # CASE 3: 05:00 UTC Cutoff with cycle semantics
    sel_05 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc), records, use_publication_cycle=True
    )
    assert sel_05 is not None
    assert sel_05.publish_time == datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    assert sel_05.publication_cycle == datetime(2026, 1, 1, 3, 30, tzinfo=timezone.utc)
    assert sel_05.generation == 18767.0


def test_explicit_0830_publication_timestamp_cutoff():
    """
    Test explicitly verifying:
    - An 08:30 publication timestamp is excluded for an 08:00 cutoff.
    - It is selected for a 09:00 cutoff if it is the latest eligible forecast.

    Note: These records use hypothetical publish times (05:30, 08:30) that happen to
    coincide with cycle times, so both raw and cycle modes produce the same result.
    """
    delivery = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=1500, publish_iso="2026-01-01T05:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=2200, publish_iso="2026-01-01T08:30:00Z"),
    ]

    # For 08:00 cutoff: raw 05:30 → cycle 05:30 (4<=5<6), raw 08:30 → cycle 08:30 (7<=8<9).
    # Cycle 08:30 >= 08:00 → excluded. Cycle 05:30 < 08:00 → selected.
    sel_08 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc), records
    )
    assert sel_08 is not None
    assert sel_08.publish_time == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert sel_08.generation == 1500.0

    # For 09:00 cutoff: cycle 08:30 < 09:00 → selected.
    sel_09 = select_forecast_for_interval(
        delivery, datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc), records
    )
    assert sel_09 is not None
    assert sel_09.publish_time == datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    assert sel_09.generation == 2200.0


# ---------------------------------------------------------------------------
# Window-level selection (propagates cycle mode by default)
# ---------------------------------------------------------------------------

def test_window_selection_uses_cycle_mode_by_default():
    """
    Verify select_forecasts_for_window uses cycle semantics by default.
    Decision date 2026-01-01, cutoff 08:00 UTC, lead 1 day → delivery 2026-01-02.
    Raw 07:30 (cycle 08:30) should be excluded; raw 04:30 (cycle 05:30) selected.
    """
    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
    ]

    result = select_forecasts_for_window(
        decision_dates=[date(2026, 1, 1)],
        cutoff_hour=8,
        cutoff_minute=0,
        lead_days=1,
        records=records,
        # No explicit use_publication_cycle → should default to True
    )

    delivery_key = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    fc = result.get(delivery_key)
    assert fc is not None
    assert fc.publish_time == datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc)
    assert fc.publication_cycle == datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert fc.generation == 18719.0


def test_window_selection_cutoff_09_selects_0830_cycle():
    """
    Window-level: cutoff 09:00 should include the 08:30 cycle (raw 07:30).
    """
    records = [
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18719, publish_iso="2026-01-01T04:30:00Z"),
        make_windfor(start_iso="2026-01-02T00:00:00Z", generation=18781, publish_iso="2026-01-01T07:30:00Z"),
    ]

    result = select_forecasts_for_window(
        decision_dates=[date(2026, 1, 1)],
        cutoff_hour=9,
        cutoff_minute=0,
        lead_days=1,
        records=records,
    )

    delivery_key = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    fc = result.get(delivery_key)
    assert fc is not None
    assert fc.publish_time == datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc)
    assert fc.publication_cycle == datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    assert fc.generation == 18781.0
