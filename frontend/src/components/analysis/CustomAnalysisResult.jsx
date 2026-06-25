/**
 * CustomAnalysisResult
 * ====================
 * Displays the result of a custom DSL-First analysis:
 *   - The chart (via DynamicChart)
 *   - Summary statistics panel
 *   - Collapsible DSL inspector
 *   - Save / re-run actions
 *
 * Props:
 *   result      {object}   The response from customAnalysisService.runFromNl / runFromDsl
 *   nlQuery     {string}   Original NL query (displayed above the chart)
 *   onRerun     {func}     Called when user clicks "Re-run"
 *   onSave      {func}     Called when user clicks "Save to analysis history"
 *   className   {string}
 */
import React, { useState, useCallback } from "react";
import DynamicChart from "./DynamicChart";
import DSLPreview from "./DSLPreview";

/* ------------------------------------------------------------------ */
/*  Statistics Panel                                                    */
/* ------------------------------------------------------------------ */
function StatisticsPanel({ stats }) {
  if (!stats || typeof stats !== "object" || !Object.keys(stats).length) {
    return null;
  }

  const fmt = (v) => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(3);
    return String(v);
  };

  return (
    <div className="custom-result__stats">
      <h4 className="custom-result__stats-title">Statistics</h4>
      <dl className="custom-result__stats-grid">
        {Object.entries(stats)
          .filter(([, v]) => typeof v !== "object")
          .map(([key, value]) => (
            <React.Fragment key={key}>
              <dt className="custom-result__stat-key">{key.replace(/_/g, " ")}</dt>
              <dd className="custom-result__stat-val">{fmt(value)}</dd>
            </React.Fragment>
          ))}
      </dl>

      {/* Trend line */}
      {stats.trend && (
        <div className="custom-result__trend">
          <span className="custom-result__trend-label">Trend:</span>
          {stats.trend.direction === "up" ? " ↑" : stats.trend.direction === "down" ? " ↓" : " →"}
          {stats.trend.slope !== undefined && (
            <span> slope {fmt(stats.trend.slope)}/period</span>
          )}
        </div>
      )}

      {/* Confidence interval */}
      {stats.confidence_interval && (
        <div className="custom-result__ci">
          <span>{stats.confidence_interval.level}% CI:</span>
          [{fmt(stats.confidence_interval.lower)}, {fmt(stats.confidence_interval.upper)}]
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Error display                                                       */
/* ------------------------------------------------------------------ */
function ErrorPanel({ result }) {
  const isColumnMissing = result.dsl_raw?.error === "column_missing";
  const isDslInsufficient = result.dsl_raw?.error === "dsl_insufficient";

  return (
    <div className="custom-result custom-result--error">
      <div className="custom-result__error-header">
        <span className="custom-result__error-icon">⚠</span>
        <strong>Analysis could not be generated</strong>
      </div>

      <p className="custom-result__error-message">{result.error}</p>

      {result.field && (
        <p className="custom-result__error-field">
          Field: <code>{result.field}</code>
        </p>
      )}
      {result.suggestion && (
        <p className="custom-result__error-suggestion">
          Suggestion: {result.suggestion}
        </p>
      )}

      {isColumnMissing && result.dsl_raw?.missing && (
        <div className="custom-result__missing-cols">
          Missing columns:
          <ul>
            {result.dsl_raw.missing.map((c) => <li key={c}><code>{c}</code></li>)}
          </ul>
        </div>
      )}

      {isDslInsufficient && (
        <p className="custom-result__escalate">
          This analysis requires a custom Python plugin (Level 5 escalation).
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                      */
/* ------------------------------------------------------------------ */
export default function CustomAnalysisResult({
  result,
  nlQuery,
  onRerun,
  onSave,
  className = "",
}) {
  const [showDsl, setShowDsl] = useState(false);

  const handleToggleDsl = useCallback(() => setShowDsl((v) => !v), []);

  if (!result) return null;

  // Error states
  if (result.status === "dsl_error") {
    return <ErrorPanel result={result} />;
  }

  const { chart_data, chart_image, statistics, dsl, generated_at } = result;

  return (
    <div className={`custom-result ${className}`}>

      {/* Query header */}
      {nlQuery && (
        <div className="custom-result__query">
          <span className="custom-result__query-label">Query:</span>
          <span className="custom-result__query-text">"{nlQuery}"</span>
        </div>
      )}

      {/* Timestamp + metadata */}
      <div className="custom-result__meta">
        {dsl?.chart?.type && (
          <span className="custom-result__chip">{dsl.chart.type}</span>
        )}
        {generated_at && (
          <span className="custom-result__timestamp">
            {new Date(generated_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Chart */}
      {chart_data && Object.keys(chart_data).length > 0 ? (
        <div className="custom-result__chart">
          <DynamicChart chartData={chart_data} />
        </div>
      ) : chart_image ? (
        <div className="custom-result__chart custom-result__chart--image">
          <img
            src={chart_image}
            alt="Custom analysis chart"
            style={{ maxWidth: "100%", borderRadius: 8 }}
          />
        </div>
      ) : (
        <p className="custom-result__no-chart">No chart data returned.</p>
      )}

      {/* Statistics */}
      <StatisticsPanel stats={statistics} />

      {/* Action bar */}
      <div className="custom-result__actions">
        <button
          className="custom-result__btn custom-result__btn--secondary"
          onClick={handleToggleDsl}
          type="button"
        >
          {showDsl ? "Hide DSL" : "Show DSL"}
        </button>

        {onRerun && (
          <button
            className="custom-result__btn custom-result__btn--secondary"
            onClick={() => onRerun(result)}
            type="button"
          >
            Re-run
          </button>
        )}

        {onSave && (
          <button
            className="custom-result__btn custom-result__btn--primary"
            onClick={() => onSave(result)}
            type="button"
          >
            Save to History
          </button>
        )}
      </div>

      {/* DSL inspector (collapsible) */}
      {showDsl && dsl && (
        <div className="custom-result__dsl-section">
          <DSLPreview dsl={dsl} />
        </div>
      )}

    </div>
  );
}
