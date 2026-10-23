"""
Wind Intelligence — Application configuration.

Loads all settings from environment variables with sensible defaults.
Uses Pydantic Settings for validation and type coercion.

Key design notes:
    - DECISION_CUTOFF_HOUR/MINUTE: prototype assumption (08:00 UTC), not a
      verified market gate-closure time.
    - DECISION_LEAD_DAYS: delivery = decision_date + lead_days (default 1 = day-ahead).
    - ANALYSIS_YEAR/MONTH: defines the decision window (Jan 2026 by default).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Elexon API
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"

    # Decision cutoff — prototype assumption, not a verified market deadline
    decision_cutoff_hour: int = 8
    decision_cutoff_minute: int = 0

    # Day-ahead lead: delivery_date = decision_date + lead_days
    decision_lead_days: int = 1

    # Analysis window (decision dates)
    analysis_year: int = 2026
    analysis_month: int = 1

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
