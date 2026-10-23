# Wind Intelligence — UK Day-Ahead Wind Forecast Accuracy Lab

An enterprise analytics dashboard and FastAPI backend evaluating the accuracy of UK national wind generation forecasts against outturn actuals using the **Elexon Insights Solution (BMRS API v1)**.

---

## Overview

In Great Britain's electricity market, day-ahead wind forecasts inform generation scheduling, system balancing, and energy trading decisions. This application compares day-ahead wind power forecasts (`WINDFOR` dataset) against aggregated actual generation outturn (`FUELHH` dataset) across January 2026.

All market generation and forecast data is streamed directly from official Elexon APIs. **Zero synthetic or mock data is used.**

---

## Key Features

- **Strict Day-Ahead Decision Cutoff**: Ensures market fidelity by selecting forecasts published strictly before the decision cutoff on the decision day ($T-1$) for delivery on day $T$ (default 08:00 UTC). Prevents future lookahead bias.
- **Conservative Publication-Cycle Handling**: Elexon BMRS wind forecast streams report raw `publishTime` timestamps (e.g., 04:30, 07:30 UTC) that correspond to official Elexon publication cycles (05:30, 08:30 UTC). Under the conservative market rule, a forecast is eligible only when its verified publication cycle is strictly earlier than the decision cutoff (e.g., at an 08:00 cutoff, the 05:30 cycle is selected; the 08:30 cycle becomes eligible at 09:00 cutoff).
- **Half-Hourly to Hourly Settlement Aggregation**: Aggregates 30-minute settlement periods (`:00` and `:30`) to hourly averages.
- **Republication Deduplication**: Resolves duplicate BMRS records at the same settlement start time by prioritizing the record with the latest publish timestamp.
- **Data Quality & Completeness Engine**: Detects and flags partial actuals (single half-hour readings), missing forecasts, and gaps in settlement data. Excludes partial intervals from primary metrics by default.
- **Comprehensive Statistical Metrics**:
  - **MAE (Mean Absolute Error)**: Average error magnitude in MW.
  - **RMSE (Root Mean Square Error)**: Metric penalizing large forecast excursions.
  - **Mean Bias**: Directional bias (+ indicates over-forecasting, − indicates under-forecasting).
  - **WAPE (Weighted Absolute Percentage Error)**: Ratio of total error to total actual generation ($\Sigma |e| / \Sigma a$), preventing division-by-zero on low wind intervals.
  - **MAPE (Mean Absolute Percentage Error)**: Per-interval percentage error evaluated over non-zero actuals.
- **Interactive UI & Visualizations**:
  - Synchronized Recharts area/line chart with zoom & pan brush.
  - Quick-preset range selectors (Week 1–4, Full Month) and decision cutoff selector.
  - Searchable and filterable hourly verification table with CSV export.
  - Methodology inspection modal.

---

## Architecture & Technology Stack

### Backend (`FastAPI`)
- **FastAPI / Pydantic v2**: High-performance async API with strict request/response schema validation and camelCase serialization.
- **httpx**: Async HTTP client with rate-limiting backoff (HTTP 429) and automatic chunking for multi-week streams.
- **pytest & pytest-asyncio**: Unit and integration test suite with synthetic fixtures.

### Frontend (`React` + `Vite` + `TypeScript`)
- **React 19 & TypeScript**: Strict type safety mirroring backend models.
- **Recharts**: Timeseries visualization with custom tooltips, gradients, and brush controls.
- **Lucide React**: Clean SVG iconography.
- **Custom Vanilla CSS**: Sleek dark luxury design system with glassmorphism, responsive cards, and curated HSL color tokens.

---

## Getting Started

### Prerequisites
- Python 3.11+ (or `uv`)
- Node.js 18+ and `npm`
- (Optional) Docker & Docker Compose

### 1. Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Default settings:
```ini
ELEXON_BASE_URL=https://data.elexon.co.uk/bmrs/api/v1
DECISION_CUTOFF_HOUR=8
DECISION_CUTOFF_MINUTE=0
DECISION_LEAD_DAYS=1
ANALYSIS_YEAR=2026
ANALYSIS_MONTH=1
VITE_API_BASE_URL=http://localhost:8000
```

---

### 2. Running Locally

#### Backend
```bash
cd backend
# Using uv (recommended)
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```
API Documentation will be accessible at: `http://localhost:8000/docs`

#### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### 3. Running with Docker Compose

```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

---

### 4. Running Backend Tests

```bash
cd backend
.\.venv\Scripts\pytest -v
```

All 39 tests cover:
- Metric calculations (MAE, RMSE, Mean Bias, WAPE, MAPE with zero-actual handling)
- Deduplication and half-hourly aggregation rules
- Strict cutoff boundaries and publication cycle mapping (`05:30` vs `08:30` cycles)
- Data gap and missing interval handling

---

## Data Provenance

All generation outturn and forecast data comes from the [Elexon Insights Solution (BMRS)](https://data.elexon.co.uk):
- **Actuals**: `GET /datasets/FUELHH/stream` (`fuelType = "WIND"`)
- **Forecasts**: `GET /datasets/WINDFOR/stream`

License / Attribution: Contains BMRS data &copy; Elexon Limited copyright and database right 2026.
