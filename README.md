# Wind Intelligence — UK Day-Ahead Wind Forecast Accuracy Lab

An interactive React dashboard and FastAPI backend for evaluating UK wind-generation forecasts against reported generation outturn using the official Elexon BMRS API.

## Live Demo

- **Frontend Dashboard:** https://uk-wind-forecast-analysis.vercel.app/
- **Backend API:** https://uk-wind-forecast-analysis.onrender.com
- **API Documentation (Swagger):** https://uk-wind-forecast-analysis.onrender.com/docs
- **Backend Health Check:** https://uk-wind-forecast-analysis.onrender.com/health
- **Source Code:** https://github.com/Ajinkyakakade02/uk-wind-forecast-analysis
- **AI Assistance Disclosure:** [AI_DISCLOSURE.md](./AI_DISCLOSURE.md)

The frontend is hosted on Vercel, and the backend is deployed on Render's free web-service instance. The backend may spin down after inactivity, so the first request after a quiet period can take longer to respond.

## Overview

Day-ahead wind forecasts can support generation scheduling, system balancing, and energy-trading decisions. This project compares records from Elexon's `WINDFOR` forecast dataset with wind-generation outturn from `FUELHH` over a January 2026 decision-date window.

The production dashboard retrieves forecast and actual-generation data from the Elexon API through the backend. It does not present synthetic or AI-generated values as market data. Synthetic fixtures are used in automated tests only.

### Decision Dates vs. Delivery Dates

The selected date range represents **decision dates**, not the delivery dates displayed in the table.

With decision dates from 1 January through 31 January 2026 and a one-day lead, the 744 hourly delivery intervals run from **2 January 2026 00:00 UTC through 1 February 2026 23:00 UTC**. This explains why the final delivery date can fall on 1 February.

## Features

- **Configurable day-ahead cutoff analysis:** Compare forecast selections at different UTC decision cutoffs. The default is 08:00 UTC.
- **Publication-cycle eligibility:** Select forecasts using the application's mapped publication-cycle time and enforce a strict `publication cycle < decision cutoff` rule.
- **Hourly actual aggregation:** Aggregate half-hourly `FUELHH` readings at `:00` and `:30` into an hourly mean.
- **Duplicate handling:** Deduplicate repeated records for the same interval using the latest available publication timestamp.
- **Data-quality reporting:** Identify missing forecasts, missing actuals, and partial actual intervals. Partial intervals are excluded from primary metrics by default.
- **Accuracy metrics:** MAE, RMSE, mean bias, WAPE, and MAPE over non-zero actuals.
- **Interactive dashboard:** Time-series chart with brush-based zooming, week/month presets, cutoff selection, searchable and filterable hourly table, and CSV export.

## Methodology and Assumptions

### Decision Cutoff

The cutoff is a configurable analysis scenario, with 08:00 UTC as the default. It is a **prototype assumption, not a claim that 08:00 UTC is an officially verified UK market gate-closure deadline**.

For each decision date, the backend evaluates forecasts for delivery one day later and excludes publication cycles that are not strictly earlier than the selected cutoff.

### Publication-Cycle Mapping

The API records expose raw `publishTime` values that can differ from the publication-cycle times used for cutoff eligibility. For example, the dashboard shows a raw time of `04:30 UTC` mapped to a `05:30 UTC` cycle and a raw time of `07:30 UTC` mapped to an `08:30 UTC` cycle.

The application uses its configured publication-cycle mapping to evaluate cutoff eligibility while retaining the raw source timestamp for inspection.

**Important limitation:** The mapped cycle is a methodological assumption based on the publication schedule used by the application. The raw API timestamp alone does not independently prove the exact moment a forecast became available to every market participant. This assumption should be considered when interpreting the results.

### Actual-Generation Aggregation

For each delivery hour, the application averages the two half-hour `FUELHH` readings at `:00` and `:30`.

If only one reading is available, the interval is flagged as partial. Partial intervals are excluded from the primary metrics unless the `include_partial` option is enabled.

### Metrics

Let forecast be `F` and actual generation be `A`:

- **MAE (Mean Absolute Error):** Mean of `|F − A|`, measured in MW.
- **RMSE (Root Mean Square Error):** Square root of the mean squared error, measured in MW. Larger errors receive more weight.
- **Mean Bias:** Mean of `F − A`. Positive values indicate over-forecasting; negative values indicate under-forecasting.
- **WAPE (Weighted Absolute Percentage Error):** `sum(|F − A|) / sum(|A|) × 100%`. This aggregates absolute errors relative to total absolute actual generation instead of dividing each interval by its actual value. It is undefined if total absolute actual generation is zero.
- **MAPE (Mean Absolute Percentage Error):** Mean of `|F − A| / |A| × 100%` for intervals where actual generation is non-zero. Zero-actual intervals are excluded from MAPE.

Coverage and missing/partial interval counts are reported alongside the accuracy metrics so forecast performance can be interpreted together with data completeness.

## Architecture and Technology Stack

### Backend

- **Python 3.12**
- **FastAPI:** API framework
- **Pydantic:** Request and response validation
- **httpx:** HTTP requests to the Elexon API
- **pandas:** Data processing
- **pytest and pytest-asyncio:** Automated tests

### Frontend

- **React 19, TypeScript, and Vite**
- **Recharts:** Interactive time-series charts
- **Lucide React:** Icons
- **Custom CSS:** Responsive dashboard styling and visual design

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── .env.example
├── .gitignore
├── AI_DISCLOSURE.md
├── docker-compose.yml
└── README.md
```

## Run Locally

### Prerequisites

- Python 3.12 recommended
- Node.js **20.19+ or 22.12+** and npm
- Git
- Optional: Docker Desktop and Docker Compose

### 1. Start the Backend

From the repository root:

**Windows PowerShell**

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**macOS / Linux**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The local API documentation is available at `http://localhost:8000/docs`, and the health endpoint is `http://localhost:8000/health`.

The backend uses its configured defaults for the Elexon API and January 2026 analysis window. Configure any required backend-specific environment variables according to the existing project configuration. Never commit real secrets or credentials.

### 2. Start the Frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
```

Create `frontend/.env.local` with the following local API setting:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

Then start Vite:

```bash
npm run dev
```

Open `http://localhost:5173` in your browser.

Vite reads `VITE_` environment variables during the frontend build. In production, the deployed frontend uses the Vercel environment variable described below.

### 3. Run Backend Tests

From the repository root:

**Windows PowerShell**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v backend\tests
```

**macOS / Linux**

```bash
backend/.venv/bin/python -m pytest -v backend/tests
```

The existing backend test suite contains 39 tests covering metric calculations, duplicate handling, half-hour aggregation, cutoff boundaries, publication-cycle mapping, and missing-data cases.

Re-run the test suite after making code changes.

### 4. Docker Compose (Optional)

The repository includes a Docker Compose configuration:

```bash
docker compose up --build
```

The intended local addresses are:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

**Docker Compose was not verified in the original development environment because the Docker daemon was unavailable.** Validate the build and startup on a machine with Docker running before relying on this workflow.

## Production Configuration

- **Frontend hosting:** Vercel
- **Backend hosting:** Render Web Service
- **Production frontend:** https://uk-wind-forecast-analysis.vercel.app/
- **Production backend:** https://uk-wind-forecast-analysis.onrender.com
- **Frontend API environment variable:** `VITE_API_BASE_URL`
- **Production API base URL:** `https://uk-wind-forecast-analysis.onrender.com`

The backend CORS allow-list includes the production Vercel frontend origin:

`https://uk-wind-forecast-analysis.vercel.app`

If either service is redeployed with configuration changes, verify the frontend and API together. Render's free service can spin down after inactivity, so the first request after a quiet period may be delayed.

## Data Provenance and Attribution

The application obtains data from the [Elexon Insights Solution (BMRS)](https://data.elexon.co.uk):

- **Actual wind generation:** `FUELHH` dataset, filtered to `fuelType = "WIND"`
- **Forecasts:** `WINDFOR` dataset

The backend uses the dataset stream endpoints and processes the returned records for the selected decision/delivery window. Data availability and publication-history details are subject to the upstream API.

**Attribution:** Contains BMRS data © Elexon Limited copyright and database right 2026.

## AI Assistance

AI-powered coding assistance was used during development. See [AI_DISCLOSURE.md](./AI_DISCLOSURE.md) for details about the scope of assistance and the developer review statement.
