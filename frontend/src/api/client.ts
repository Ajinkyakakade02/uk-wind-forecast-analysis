/**
 * Wind Intelligence — Frontend API client.
 *
 * Typed fetch client for communicating with the FastAPI backend.
 * To be fully wired up in Phase 5.
 */

import type { AnalysisConfig, AnalysisResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchConfig(): Promise<AnalysisConfig> {
  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) {
    throw new Error(`Failed to fetch config: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAnalysis(params?: {
  cutoffHour?: number;
  startDate?: string;
  endDate?: string;
  includePartial?: boolean;
}): Promise<AnalysisResponse> {
  const query = new URLSearchParams();
  if (params?.cutoffHour !== undefined) query.set('cutoff_hour', params.cutoffHour.toString());
  if (params?.startDate) query.set('start_date', params.startDate);
  if (params?.endDate) query.set('end_date', params.endDate);
  if (params?.includePartial !== undefined) query.set('include_partial', params.includePartial.toString());

  const url = `${API_BASE}/api/analysis${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch analysis: ${res.statusText}`);
  }
  return res.json();
}
