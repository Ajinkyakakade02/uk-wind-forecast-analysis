import React from 'react';
import type { WindDataFilters } from '../hooks/useWindData';
import { Calendar, Clock, RefreshCw, Filter } from 'lucide-react';

interface Props {
  filters: WindDataFilters;
  onChange: (updated: Partial<WindDataFilters>) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const DateRangePicker: React.FC<Props> = ({
  filters,
  onChange,
  onRefresh,
  loading,
}) => {
  const presets = [
    { label: 'Full Month (Jan 2026)', start: '2026-01-01', end: '2026-01-31' },
    { label: 'Week 1 (Jan 1-7)', start: '2026-01-01', end: '2026-01-07' },
    { label: 'Week 2 (Jan 8-14)', start: '2026-01-08', end: '2026-01-14' },
    { label: 'Week 3 (Jan 15-21)', start: '2026-01-15', end: '2026-01-21' },
    { label: 'Week 4 (Jan 22-31)', start: '2026-01-22', end: '2026-01-31' },
  ];

  return (
    <div className="filter-bar glass-panel">
      {/* Presets */}
      <div className="preset-group">
        <span className="filter-group-title">
          <Filter size={14} /> Presets:
        </span>
        {presets.map((p) => {
          const isActive = filters.startDate === p.start && filters.endDate === p.end;
          return (
            <button
              key={p.label}
              type="button"
              className={`preset-btn ${isActive ? 'active' : ''}`}
              onClick={() => onChange({ startDate: p.start, endDate: p.end })}
            >
              {p.label}
            </button>
          );
        })}
      </div>

      <div className="filter-inputs-row">
        {/* Date Inputs */}
        <div className="filter-field">
          <label>
            <Calendar size={14} /> Start Date
          </label>
          <input
            type="date"
            value={filters.startDate}
            min="2026-01-01"
            max="2026-01-31"
            onChange={(e) => onChange({ startDate: e.target.value })}
            className="input-control"
          />
        </div>

        <div className="filter-field">
          <label>
            <Calendar size={14} /> End Date
          </label>
          <input
            type="date"
            value={filters.endDate}
            min="2026-01-01"
            max="2026-01-31"
            onChange={(e) => onChange({ endDate: e.target.value })}
            className="input-control"
          />
        </div>

        {/* Cutoff Selector */}
        <div className="filter-field">
          <label>
            <Clock size={14} /> Decision Cutoff (UTC)
          </label>
          <select
            value={filters.cutoffHour}
            onChange={(e) => onChange({ cutoffHour: parseInt(e.target.value, 10) })}
            className="select-control"
          >
            <option value={6}>06:00 UTC</option>
            <option value={7}>07:00 UTC</option>
            <option value={8}>08:00 UTC (Default Day-Ahead)</option>
            <option value={9}>09:00 UTC</option>
            <option value={10}>10:00 UTC</option>
            <option value={11}>11:00 UTC</option>
            <option value={12}>12:00 UTC</option>
          </select>
        </div>

        {/* Refresh Button */}
        <div className="filter-field refresh-field">
          <button
            type="button"
            className="refresh-btn"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>{loading ? 'Fetching...' : 'Update Analysis'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
