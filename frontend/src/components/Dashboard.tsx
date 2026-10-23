import React, { useState } from 'react';
import { useWindData } from '../hooks/useWindData';
import { AccuracyMetrics } from './AccuracyMetrics';
import { DataQuality } from './DataQuality';
import { DateRangePicker } from './DateRangePicker';
import { ForecastChart } from './ForecastChart';
import { DataTable } from './DataTable';
import { Wind, Info, ExternalLink, Activity, X } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { data, loading, error, filters, updateFilters, refetch } = useWindData();
  const [showMethodology, setShowMethodology] = useState<boolean>(false);

  return (
    <div className="app-layout">
      {/* Top Navigation / App Header */}
      <header className="app-header glass-panel">
        <div className="header-left">
          <div className="brand-logo">
            <div className="logo-icon-wrap">
              <Wind size={22} className="logo-svg" />
            </div>
            <div>
              <div className="brand-title-row">
                <h1 className="brand-title">Wind Intelligence</h1>
                <span className="brand-badge">UK BMRS v1</span>
              </div>
              <p className="brand-desc">
                Day-Ahead Wind Forecast Accuracy Evaluation & Outturn Verification
              </p>
            </div>
          </div>
        </div>

        <div className="header-right">
          <div className="live-status-pill">
            <span className="pulsing-dot" />
            <span>Elexon Live Stream Connected</span>
          </div>

          <button
            type="button"
            className="methodology-btn"
            onClick={() => setShowMethodology(true)}
          >
            <Info size={15} />
            <span>Methodology</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="dashboard-main">
        {/* Error notification banner if any */}
        {error && (
          <div className="error-banner">
            <span>Unable to load live data: {error}</span>
            <button type="button" onClick={refetch}>Retry</button>
          </div>
        )}

        {/* Filter Bar */}
        <DateRangePicker
          filters={filters}
          onChange={updateFilters}
          onRefresh={refetch}
          loading={loading}
        />

        {/* Metrics Grid */}
        <section className="section-block">
          <div className="section-title-row">
            <h2>Accuracy Benchmarks</h2>
            <span className="section-hint">
              Evaluating day-ahead forecasts against outturn actuals at {filters.cutoffHour.toString().padStart(2, '0')}:00 UTC cutoff
            </span>
          </div>
          <AccuracyMetrics
            metrics={data?.metrics ?? { mae: null, rmse: null, meanBias: null, wape: null }}
            loading={loading}
          />
        </section>

        {/* Data Quality & Completeness */}
        <section className="section-block">
          <DataQuality
            quality={
              data?.dataQuality ?? {
                totalDeliveryHours: 0,
                matchedIntervals: 0,
                missingForecastIntervals: 0,
                missingActualIntervals: 0,
                partialActualIntervals: 0,
              }
            }
            includePartial={filters.includePartial}
            onTogglePartial={(inc) => updateFilters({ includePartial: inc })}
            loading={loading}
          />
        </section>

        {/* Interactive Timeseries Chart */}
        <section className="section-block">
          <ForecastChart
            intervals={data?.intervals ?? []}
            loading={loading}
          />
        </section>

        {/* Detailed Data Table */}
        <section className="section-block">
          <DataTable
            intervals={data?.intervals ?? []}
            loading={loading}
          />
        </section>
      </main>

      {/* Methodology Drawer / Modal */}
      {showMethodology && (
        <div className="modal-overlay" onClick={() => setShowMethodology(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <Activity size={20} className="text-cyan" />
                <h3>Wind Intelligence — Verification Methodology</h3>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={() => setShowMethodology(false)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div className="methodology-card">
                <h4>1. Strict Decision Cutoff Rule</h4>
                <p>
                  To prevent future lookahead bias, for each decision date <code>D</code> and delivery hour <code>H</code> on day <code>D + 1</code>,
                  only WINDFOR forecasts published <strong>strictly before</strong> the decision cutoff (default 08:00 UTC) are considered:
                  <br />
                  <code>publishTime &lt; cutoff</code> (never <code>&le;</code>, never after).
                  Among all eligible forecasts, the one with the latest publish time is chosen.
                </p>
              </div>

              <div className="methodology-card">
                <h4>2. Half-Hourly to Hourly Actual Aggregation</h4>
                <p>
                  Actual generation values from the <code>FUELHH</code> stream (filtered to <code>fuelType = WIND</code>) are reported in 30-minute settlement periods.
                  For each hour <code>H</code>:
                </p>
                <ul>
                  <li>Both <code>H:00</code> and <code>H:30</code> present &rarr; <code>Hourly Actual = (H:00 + H:30) / 2</code></li>
                  <li>Only one half-hour present &rarr; Flagged as <strong>partial actual</strong> (excluded from primary metrics by default to avoid bias)</li>
                  <li>Neither present &rarr; Flagged as missing</li>
                </ul>
              </div>

              <div className="methodology-card">
                <h4>3. Republication Deduplication</h4>
                <p>
                  If multiple FUELHH records exist for the exact same start time (due to revised settlement runs or republications),
                  the record with the latest <code>publishTime</code> is selected before aggregation.
                </p>
              </div>

              <div className="methodology-card">
                <h4>4. Robust Accuracy Metrics</h4>
                <ul>
                  <li><strong>MAE (Mean Absolute Error):</strong> Average absolute deviation in MW.</li>
                  <li><strong>RMSE:</strong> Square root of mean squared error; penalizes high error excursions.</li>
                  <li><strong>Mean Bias:</strong> Average signed difference (forecast − actual); indicates systematic over/under forecasting.</li>
                  <li><strong>WAPE:</strong> &Sigma;|Error| / &Sigma;|Actual|; mathematically avoids division by zero on low generation hours.</li>
                </ul>
              </div>

              <div className="methodology-card">
                <h4>5. Data Provenance</h4>
                <p>
                  All data is streamed live from Great Britain's official energy market data provider:
                  <a
                    href="https://data.elexon.co.uk"
                    target="_blank"
                    rel="noreferrer"
                    className="modal-link"
                  >
                    Elexon Insights Solution (BMRS API v1) <ExternalLink size={12} />
                  </a>.
                  Zero mock or synthetic data is displayed.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div>
          <span>Data source: </span>
          <a href="https://data.elexon.co.uk" target="_blank" rel="noreferrer">
            Elexon Insights Solution (BMRS API v1)
          </a>
          <span> &bull; Datasets: FUELHH (Actuals) &amp; WINDFOR (Day-Ahead Forecasts)</span>
        </div>
        <div>
          <span>Antigravity Wind Intelligence Lab &bull; January 2026 Outturn Analysis</span>
        </div>
      </footer>
    </div>
  );
};
