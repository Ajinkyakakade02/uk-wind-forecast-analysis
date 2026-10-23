/**
 * Wind Intelligence — Formatting utilities.
 *
 * Helper functions for formatting dates, numbers, and generation values.
 */

export function formatMW(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${Math.round(val).toLocaleString()} MW`;
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${val.toFixed(1)}%`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toISOString().replace('.000Z', 'Z').replace('T', ' ');
}
