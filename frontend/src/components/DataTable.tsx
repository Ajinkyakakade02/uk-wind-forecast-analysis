import React, { useState, useMemo } from 'react';
import type { HourlyComparison } from '../types';
import { formatMW, formatDateTime } from '../utils/formatters';
import { Table, Download, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface Props {
  intervals: HourlyComparison[];
  loading?: boolean;
}

export const DataTable: React.FC<Props> = ({ intervals, loading }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'matched' | 'partial' | 'missing' | 'large_error'>('all');
  const [page, setPage] = useState(1);
  const pageSize = 24; // 1 delivery day per page

  // Filtered rows
  const filtered = useMemo(() => {
    return intervals.filter((row) => {
      // Search term
      if (searchTerm) {
        const timeStr = row.startTime.toLowerCase();
        if (!timeStr.includes(searchTerm.toLowerCase())) return false;
      }

      // Status filter
      if (statusFilter === 'matched') {
        return !row.isMissingForecast && !row.isMissingActual && !row.isPartialActual;
      }
      if (statusFilter === 'partial') {
        return row.isPartialActual;
      }
      if (statusFilter === 'missing') {
        return row.isMissingForecast || row.isMissingActual;
      }
      if (statusFilter === 'large_error') {
        return row.absoluteError !== null && row.absoluteError >= 2000;
      }
      return true;
    });
  }, [intervals, searchTerm, statusFilter]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pagedRows = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // CSV Export
  const downloadCSV = () => {
    const headers = [
      'Delivery Interval UTC',
      'Day-Ahead Forecast (MW)',
      'Raw Publish Time UTC',
      'Publication Cycle UTC',
      'Actual Generation (MW)',
      'Partial Actual Flag',
      'Missing Actual Flag',
      'Missing Forecast Flag',
      'Signed Error (MW)',
      'Absolute Error (MW)',
    ];

    const rows = intervals.map((i) => [
      i.startTime,
      i.forecastGeneration ?? '',
      i.forecastPublishTime ?? '',
      i.forecastPublicationCycle ?? '',
      i.actualGeneration ?? '',
      i.isPartialActual ? 'TRUE' : 'FALSE',
      i.isMissingActual ? 'TRUE' : 'FALSE',
      i.isMissingForecast ? 'TRUE' : 'FALSE',
      i.signedError ?? '',
      i.absoluteError ?? '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `wind_forecast_accuracy_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="table-panel glass-panel">
      <div className="table-header-row">
        <div className="table-title-area">
          <Table className="accent-icon" size={20} />
          <div>
            <h3>Hourly Verification Data Table</h3>
            <span className="table-caption">
              Detailed breakdown of matched intervals, selected publish cutoffs, and outturn actuals
            </span>
          </div>
        </div>

        <div className="table-action-area">
          {/* Status Filter Buttons */}
          <div className="table-filter-pills">
            <button
              type="button"
              className={`pill-btn ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('all'); setPage(1); }}
            >
              All ({intervals.length})
            </button>
            <button
              type="button"
              className={`pill-btn ${statusFilter === 'matched' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('matched'); setPage(1); }}
            >
              Matched
            </button>
            <button
              type="button"
              className={`pill-btn ${statusFilter === 'large_error' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('large_error'); setPage(1); }}
            >
              Error &gt; 2k MW
            </button>
            <button
              type="button"
              className={`pill-btn ${statusFilter === 'partial' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('partial'); setPage(1); }}
            >
              Partial (1/2 hr)
            </button>
            <button
              type="button"
              className={`pill-btn ${statusFilter === 'missing' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('missing'); setPage(1); }}
            >
              Missing
            </button>
          </div>

          {/* Search Box */}
          <div className="table-search-box">
            <Search size={14} />
            <input
              type="text"
              placeholder="Filter by date..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
            />
          </div>

          {/* Export CSV Button */}
          <button type="button" className="csv-btn" onClick={downloadCSV}>
            <Download size={14} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Element */}
      <div className="table-scroll-container">
        <table className="verification-table">
          <thead>
            <tr>
              <th>Delivery Interval (UTC)</th>
              <th>Selected Forecast (MW)</th>
              <th>Forecast Publish Time (UTC)</th>
              <th>Actual Generation (MW)</th>
              <th>Signed Error (F − A)</th>
              <th>Absolute Error</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="table-loading-cell">Loading records...</td>
              </tr>
            ) : pagedRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="table-empty-cell">No matching records found.</td>
              </tr>
            ) : (
              pagedRows.map((row) => {
                const isOver = (row.signedError ?? 0) > 0;
                const isUnder = (row.signedError ?? 0) < 0;

                return (
                  <tr key={row.startTime} className={row.isPartialActual ? 'row-partial' : ''}>
                    <td className="font-mono">{formatDateTime(row.startTime)}</td>
                    <td className="font-mono font-semibold text-cyan">
                      {formatMW(row.forecastGeneration)}
                    </td>
                    <td className="font-mono text-muted text-xs">
                      {row.forecastPublishTime ? (
                        <div>
                          <div>{formatDateTime(row.forecastPublishTime)}</div>
                          {row.forecastPublicationCycle && (
                            <div className="text-cyan" style={{ fontSize: '10px' }}>
                              Cycle: {formatDateTime(row.forecastPublicationCycle).slice(11, 16)} UTC
                            </div>
                          )}
                        </div>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="font-mono font-semibold text-emerald">
                      {formatMW(row.actualGeneration)}
                    </td>
                    <td className={`font-mono ${isOver ? 'text-amber' : isUnder ? 'text-blue' : ''}`}>
                      {row.signedError !== null
                        ? `${row.signedError > 0 ? '+' : ''}${formatMW(row.signedError)}`
                        : '—'}
                    </td>
                    <td className="font-mono">
                      {formatMW(row.absoluteError)}
                    </td>
                    <td>
                      {row.isMissingForecast && (
                        <span className="status-badge badge-missing-fc">Missing Forecast</span>
                      )}
                      {row.isMissingActual && (
                        <span className="status-badge badge-missing-act">Missing Actual</span>
                      )}
                      {row.isPartialActual && (
                        <span className="status-badge badge-partial">Partial (1/2 hr)</span>
                      )}
                      {!row.isMissingForecast && !row.isMissingActual && !row.isPartialActual && (
                        <span className="status-badge badge-matched">Matched</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="table-pagination-row">
        <span className="pagination-info">
          Showing {filtered.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filtered.length)} of {filtered.length} intervals
        </span>
        <div className="pagination-btns">
          <button
            type="button"
            className="pager-btn"
            disabled={currentPage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <span className="page-indicator">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="pager-btn"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
