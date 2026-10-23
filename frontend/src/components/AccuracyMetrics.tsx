import React from 'react';
import type { AccuracyMetrics as AccuracyMetricsType } from '../types';
import { formatMW, formatPercent } from '../utils/formatters';
import { Activity, Gauge, TrendingUp, TrendingDown, Percent, AlertCircle } from 'lucide-react';

interface Props {
  metrics: AccuracyMetricsType;
  loading?: boolean;
}

export const AccuracyMetrics: React.FC<Props> = ({ metrics, loading }) => {
  const isOverForecast = (metrics.meanBias ?? 0) > 0;
  const isUnderForecast = (metrics.meanBias ?? 0) < 0;

  return (
    <div className="metrics-grid">
      {/* MAE Card */}
      <div className="metric-card glass-panel">
        <div className="metric-header">
          <span className="metric-label">Mean Absolute Error (MAE)</span>
          <div className="metric-icon-wrap cyan">
            <Gauge size={18} />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-value">{loading ? '...' : formatMW(metrics.mae)}</span>
        </div>
        <div className="metric-subtext">Average magnitude of forecast deviation</div>
      </div>

      {/* RMSE Card */}
      <div className="metric-card glass-panel">
        <div className="metric-header">
          <span className="metric-label">Root Mean Square Error (RMSE)</span>
          <div className="metric-icon-wrap violet">
            <Activity size={18} />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-value">{loading ? '...' : formatMW(metrics.rmse)}</span>
        </div>
        <div className="metric-subtext">Penalizes large outlier forecast errors</div>
      </div>

      {/* Mean Bias Card */}
      <div className="metric-card glass-panel">
        <div className="metric-header">
          <span className="metric-label">Mean Bias</span>
          <div className={`metric-icon-wrap ${isOverForecast ? 'amber' : isUnderForecast ? 'blue' : 'emerald'}`}>
            {isOverForecast ? <TrendingUp size={18} /> : isUnderForecast ? <TrendingDown size={18} /> : <Activity size={18} />}
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-value">
            {loading ? '...' : metrics.meanBias !== null ? `${metrics.meanBias > 0 ? '+' : ''}${formatMW(metrics.meanBias)}` : '—'}
          </span>
          {!loading && metrics.meanBias !== null && (
            <span className={`bias-tag ${isOverForecast ? 'tag-amber' : isUnderForecast ? 'tag-blue' : 'tag-emerald'}`}>
              {isOverForecast ? 'Over-forecast' : isUnderForecast ? 'Under-forecast' : 'Neutral'}
            </span>
          )}
        </div>
        <div className="metric-subtext">Directional tendency (+ over, − under)</div>
      </div>

      {/* WAPE Card */}
      <div className="metric-card glass-panel">
        <div className="metric-header">
          <span className="metric-label">Weighted Absolute % Error (WAPE)</span>
          <div className="metric-icon-wrap emerald">
            <Percent size={18} />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-value">{loading ? '...' : formatPercent(metrics.wape)}</span>
        </div>
        <div className="metric-subtext">Σ|Error| / Σ|Actual| (Zero-division proof)</div>
      </div>

      {/* Optional MAPE Card */}
      {metrics.mape !== undefined && metrics.mape !== null && (
        <div className="metric-card glass-panel">
          <div className="metric-header">
            <span className="metric-label">MAPE (Non-Zero Actuals)</span>
            <div className="metric-icon-wrap rose">
              <Percent size={18} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{loading ? '...' : formatPercent(metrics.mape)}</span>
            {metrics.mapeExcludedCount ? (
              <span className="excluded-tag" title="Intervals where actual = 0 excluded from MAPE">
                <AlertCircle size={12} /> {metrics.mapeExcludedCount} excluded
              </span>
            ) : null}
          </div>
          <div className="metric-subtext">Per-interval percentage error</div>
        </div>
      )}
    </div>
  );
};
