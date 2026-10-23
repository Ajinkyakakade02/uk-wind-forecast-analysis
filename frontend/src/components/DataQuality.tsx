import React from 'react';
import type { DataQuality as DataQualityType } from '../types';
import { CheckCircle2, AlertTriangle, HelpCircle, Layers, ShieldCheck } from 'lucide-react';

interface Props {
  quality: DataQualityType;
  includePartial: boolean;
  onTogglePartial?: (include: boolean) => void;
  loading?: boolean;
}

export const DataQuality: React.FC<Props> = ({
  quality,
  includePartial,
  onTogglePartial,
  loading,
}) => {
  const matchRate = quality.totalDeliveryHours > 0
    ? ((quality.matchedIntervals / quality.totalDeliveryHours) * 100).toFixed(1)
    : '0';

  return (
    <div className="data-quality-panel glass-panel">
      <div className="quality-header">
        <div className="quality-title-area">
          <ShieldCheck className="accent-icon" size={20} />
          <div>
            <h3>Data Quality & Completeness</h3>
            <span className="quality-caption">
              Evaluating Elexon FUELHH (actual generation) and WINDFOR (forecast) interval matching
            </span>
          </div>
        </div>
        <div className="match-pill">
          <span className="match-pill-pct">{loading ? '...' : `${matchRate}%`}</span>
          <span className="match-pill-label">Coverage</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="coverage-bar-track">
        <div
          className="coverage-bar-fill"
          style={{ width: `${Math.min(100, Math.max(0, parseFloat(matchRate)))}%` }}
        />
      </div>

      {/* Quality Stats Grid */}
      <div className="quality-stats-grid">
        <div className="quality-stat-box">
          <span className="stat-label">Delivery Hours</span>
          <span className="stat-val">{loading ? '...' : quality.totalDeliveryHours}</span>
          <span className="stat-sub">Target period</span>
        </div>

        <div className="quality-stat-box matched">
          <div className="stat-header-row">
            <span className="stat-label">Matched Intervals</span>
            <CheckCircle2 size={14} className="text-emerald" />
          </div>
          <span className="stat-val text-emerald">{loading ? '...' : quality.matchedIntervals}</span>
          <span className="stat-sub">Both forecast & actual present</span>
        </div>

        <div className="quality-stat-box">
          <div className="stat-header-row">
            <span className="stat-label">Missing Forecasts</span>
            {quality.missingForecastIntervals > 0 && <AlertTriangle size={14} className="text-amber" />}
          </div>
          <span className={`stat-val ${quality.missingForecastIntervals > 0 ? 'text-amber' : ''}`}>
            {loading ? '...' : quality.missingForecastIntervals}
          </span>
          <span className="stat-sub">No eligible WINDFOR record</span>
        </div>

        <div className="quality-stat-box">
          <div className="stat-header-row">
            <span className="stat-label">Missing Actuals</span>
            {quality.missingActualIntervals > 0 && <AlertTriangle size={14} className="text-rose" />}
          </div>
          <span className={`stat-val ${quality.missingActualIntervals > 0 ? 'text-rose' : ''}`}>
            {loading ? '...' : quality.missingActualIntervals}
          </span>
          <span className="stat-sub">No FUELHH records at :00 or :30</span>
        </div>

        <div className="quality-stat-box partial">
          <div className="stat-header-row">
            <span className="stat-label">Partial Actuals</span>
            <Layers size={14} className="text-blue" />
          </div>
          <span className="stat-val text-blue">{loading ? '...' : quality.partialActualIntervals}</span>
          <span className="stat-sub">Only one half-hour reported</span>
        </div>
      </div>

      {/* Partial Handling Notice */}
      <div className="partial-notice-box">
        <div className="notice-icon-wrap">
          <HelpCircle size={16} />
        </div>
        <div className="notice-content">
          <strong>Aggregation Methodology Notice:</strong>
          <span>
            Hourly actuals are computed as the arithmetic mean of the :00 and :30 half-hourly FUELHH readings.
            When only one half-hour is present, it is flagged as <em>partial</em>. By default, partial actuals are{' '}
            <strong>excluded</strong> from primary accuracy metrics (MAE/RMSE/WAPE) to preserve measurement precision.
          </span>
        </div>
        {onTogglePartial && (
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={includePartial}
              onChange={(e) => onTogglePartial(e.target.checked)}
            />
            <span className="toggle-slider" />
            <span className="toggle-text">Include in Metrics</span>
          </label>
        )}
      </div>
    </div>
  );
};
