import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
} from 'recharts';
import type { HourlyComparison } from '../types';
import { formatMW, formatDateTime } from '../utils/formatters';
import { TrendingUp, Wind, Zap, Eye, EyeOff } from 'lucide-react';

interface Props {
  intervals: HourlyComparison[];
  loading?: boolean;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const data: HourlyComparison = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="custom-chart-tooltip glass-panel">
      <div className="tooltip-time">{formatDateTime(data.startTime)} UTC</div>
      <div className="tooltip-divider" />
      <div className="tooltip-row">
        <span className="tooltip-label forecast-color">
          <Wind size={13} /> Day-Ahead Forecast:
        </span>
        <span className="tooltip-val">{formatMW(data.forecastGeneration)}</span>
      </div>
      {data.forecastPublishTime && (
        <div className="tooltip-subrow">
          <span>Published:</span>
          <span>
            {formatDateTime(data.forecastPublishTime)} UTC
            {data.forecastPublicationCycle && (
              <span style={{ color: '#06b6d4', marginLeft: '6px' }}>
                ({formatDateTime(data.forecastPublicationCycle).slice(11, 16)} UTC Cycle)
              </span>
            )}
          </span>
        </div>
      )}
      <div className="tooltip-row">
        <span className="tooltip-label actual-color">
          <Zap size={13} /> Actual Generation:
        </span>
        <span className="tooltip-val">
          {formatMW(data.actualGeneration)}
          {data.isPartialActual && <span className="partial-badge">Partial (1/2 hr)</span>}
        </span>
      </div>
      {data.signedError !== null && (
        <div className="tooltip-row">
          <span className="tooltip-label error-color">Signed Error (F − A):</span>
          <span className={`tooltip-val ${data.signedError > 0 ? 'text-amber' : 'text-blue'}`}>
            {data.signedError > 0 ? '+' : ''}{formatMW(data.signedError)}
          </span>
        </div>
      )}
      {data.absoluteError !== null && (
        <div className="tooltip-row">
          <span className="tooltip-label">Absolute Error:</span>
          <span className="tooltip-val">{formatMW(data.absoluteError)}</span>
        </div>
      )}
    </div>
  );
};

export const ForecastChart: React.FC<Props> = ({ intervals, loading }) => {
  const [showErrors, setShowErrors] = useState<boolean>(false);

  // Peak statistics
  const stats = useMemo(() => {
    let peakForecast = 0;
    let peakActual = 0;
    let sumActual = 0;
    let countActual = 0;

    for (const item of intervals) {
      if (item.forecastGeneration !== null && item.forecastGeneration > peakForecast) {
        peakForecast = item.forecastGeneration;
      }
      if (item.actualGeneration !== null) {
        if (item.actualGeneration > peakActual) peakActual = item.actualGeneration;
        sumActual += item.actualGeneration;
        countActual += 1;
      }
    }

    return {
      peakForecast,
      peakActual,
      avgActual: countActual > 0 ? sumActual / countActual : 0,
    };
  }, [intervals]);

  // Format x-axis tick labels cleanly (e.g. "02 Jan 12:00")
  const formatXAxis = (isoStr: string) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const day = d.getUTCDate();
    const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
    const hour = d.getUTCHours().toString().padStart(2, '0');
    return `${day} ${month} ${hour}:00`;
  };

  if (loading) {
    return (
      <div className="chart-panel glass-panel loading-chart">
        <div className="chart-loading-spinner" />
        <p>Loading market generation & forecast timeline...</p>
      </div>
    );
  }

  return (
    <div className="chart-panel glass-panel">
      <div className="chart-header">
        <div className="chart-title-group">
          <TrendingUp className="accent-icon" size={20} />
          <div>
            <h3>Day-Ahead Wind Forecast vs Actual Generation (MW)</h3>
            <span className="chart-subtitle">
              Interactive hourly timeseries — Drag bottom brush to pan & zoom
            </span>
          </div>
        </div>

        <div className="chart-controls">
          <div className="chart-stat-chip">
            <span className="chip-label">Peak Forecast:</span>
            <span className="chip-val text-cyan">{formatMW(stats.peakForecast)}</span>
          </div>
          <div className="chart-stat-chip">
            <span className="chip-label">Peak Actual:</span>
            <span className="chip-val text-emerald">{formatMW(stats.peakActual)}</span>
          </div>
          <button
            type="button"
            className={`toggle-error-btn ${showErrors ? 'active' : ''}`}
            onClick={() => setShowErrors(!showErrors)}
          >
            {showErrors ? <EyeOff size={14} /> : <Eye size={14} />}
            <span>{showErrors ? 'Hide Error Spread' : 'Show Error Spread'}</span>
          </button>
        </div>
      </div>

      <div className="recharts-wrapper-container" style={{ width: '100%', height: 420 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={intervals} margin={{ top: 15, right: 20, left: 10, bottom: 20 }}>
            <defs>
              <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

            <XAxis
              dataKey="startTime"
              tickFormatter={formatXAxis}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              minTickGap={45}
            />

            <YAxis
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              unit=" MW"
            />

            <Tooltip content={<CustomTooltip />} />

            <Legend
              verticalAlign="top"
              height={36}
              wrapperStyle={{ top: 0, paddingBottom: 10 }}
              formatter={(value) => (
                <span style={{ color: '#cbd5e1', fontSize: 13, fontWeight: 500 }}>{value}</span>
              )}
            />

            <Area
              type="monotone"
              dataKey="forecastGeneration"
              name="Day-Ahead Forecast"
              stroke="#06b6d4"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#forecastGradient)"
              dot={false}
              activeDot={{ r: 5, fill: '#06b6d4', stroke: '#fff', strokeWidth: 2 }}
            />

            <Area
              type="monotone"
              dataKey="actualGeneration"
              name="Actual Generation"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#actualGradient)"
              dot={false}
              activeDot={{ r: 5, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
            />

            {showErrors && (
              <Line
                type="monotone"
                dataKey="absoluteError"
                name="Absolute Error (|F − A|)"
                stroke="#f59e0b"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            )}

            <Brush
              dataKey="startTime"
              height={26}
              stroke="#06b6d4"
              fill="#0f172a"
              tickFormatter={formatXAxis}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
