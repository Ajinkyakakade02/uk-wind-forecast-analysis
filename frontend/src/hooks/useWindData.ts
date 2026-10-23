/**
 * Wind Intelligence — React hook for fetching and managing analysis data.
 */

import { useState, useEffect, useCallback } from 'react';
import type { AnalysisResponse } from '../types';
import { fetchAnalysis } from '../api/client';

export interface WindDataFilters {
  cutoffHour: number;
  startDate: string;
  endDate: string;
  includePartial: boolean;
}

export function useWindData(initialFilters?: Partial<WindDataFilters>) {
  const [filters, setFilters] = useState<WindDataFilters>({
    cutoffHour: initialFilters?.cutoffHour ?? 8,
    startDate: initialFilters?.startDate ?? '2026-01-01',
    endDate: initialFilters?.endDate ?? '2026-01-31',
    includePartial: initialFilters?.includePartial ?? false,
  });

  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const res = await fetchAnalysis({
          cutoffHour: filters.cutoffHour,
          startDate: filters.startDate,
          endDate: filters.endDate,
          includePartial: filters.includePartial,
        });
        if (!ignore) {
          setData(res);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : 'Failed to fetch data');
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, [filters, refreshTrigger]);

  const updateFilters = useCallback((newFilters: Partial<WindDataFilters>) => {
    setLoading(true);
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const refetch = useCallback(() => {
    setLoading(true);
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  return {
    data,
    loading,
    error,
    filters,
    updateFilters,
    refetch,
  };
}
