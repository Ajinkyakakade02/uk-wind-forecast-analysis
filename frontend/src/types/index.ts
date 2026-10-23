/**
 * Wind Intelligence — Frontend type definitions.
 *
 * Defines domain types and API contract shapes mirroring the backend Pydantic schemas.
 */

export interface HourlyComparison {
  startTime: string; // ISO 8601 UTC
  forecastGeneration: number | null; // MW
  forecastPublishTime: string | null; // ISO 8601 UTC
  forecastPublicationCycle?: string | null; // ISO 8601 UTC
  actualGeneration: number | null; // MW (hourly average)
  isPartialActual: boolean;
  isMissingActual: boolean;
  isMissingForecast: boolean;
  absoluteError: number | null; // MW
  signedError: number | null; // MW (forecast - actual)
}

export interface AccuracyMetrics {
  mae: number | null; // Mean Absolute Error (MW)
  rmse: number | null; // Root Mean Square Error (MW)
  meanBias: number | null; // Mean Bias (MW; + = over-forecast)
  wape: number | null; // Weighted Absolute Percentage Error (%)
  mape?: number | null; // Mean Absolute Percentage Error (optional, % where actual > 0)
  mapeExcludedCount?: number; // Intervals excluded from MAPE due to actual = 0
}

export interface DataQuality {
  totalDeliveryHours: number;
  matchedIntervals: number;
  missingForecastIntervals: number;
  missingActualIntervals: number;
  partialActualIntervals: number;
}

export interface AnalysisConfig {
  decisionCutoffHour: number;
  decisionCutoffMinute: number;
  decisionLeadDays: number;
  analysisYear: number;
  analysisMonth: number;
  elexonBaseUrl: string;
}

export interface AnalysisResponse {
  config: AnalysisConfig;
  metrics: AccuracyMetrics;
  dataQuality: DataQuality;
  intervals: HourlyComparison[];
}
