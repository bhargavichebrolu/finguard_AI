/**
 * Chart building blocks. Every chart sits in a ChartCard with a table view, so the data can be
 * read without the picture, by keyboard and by screen readers.
 */
import { useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  AXIS_TEXT,
  GRID,
  LOWERS_SCORE,
  RAISES_SCORE,
  REFERENCE,
  SERIES_PRIMARY,
  SERIES_SECONDARY,
} from "../utils/chartColors";
import { formatCount } from "../utils/format";

const CHART_HEIGHT = 260;
const AXIS_TICK = { fill: AXIS_TEXT, fontSize: 12 };

export interface TableColumn {
  key: string;
  header: string;
  numeric?: boolean;
}

export interface ChartCardProps {
  title: string;
  description?: ReactNode;
  tableColumns: TableColumn[];
  tableRows: Record<string, ReactNode>[];
  children: ReactNode;
}

/** A titled chart with a button that swaps it for a plain table of the same values. */
export function ChartCard({ title, description, tableColumns, tableRows, children }: ChartCardProps) {
  const [showTable, setShowTable] = useState(false);
  return (
    <article className="card chart-card">
      <div className="chart-header">
        <h2>{title}</h2>
        <button
          type="button"
          className="button secondary small-button"
          aria-pressed={showTable}
          onClick={() => setShowTable((value) => !value)}
        >
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>
      {description ? <p className="muted small">{description}</p> : null}
      {showTable ? (
        <div className="table-wrap">
          <table className="data-table">
            <caption className="visually-hidden">{title}</caption>
            <thead>
              <tr>
                {tableColumns.map((column) => (
                  <th key={column.key} scope="col" className={column.numeric ? "numeric" : undefined}>
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row, index) => (
                <tr key={index}>
                  {tableColumns.map((column) => (
                    <td key={column.key} className={column.numeric ? "numeric" : undefined}>
                      {row[column.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart-area" aria-hidden="true">
          {children}
        </div>
      )}
    </article>
  );
}

export interface CategoryDatum {
  label: string;
  value: number;
}

/** Legend entries in text ink, so the coloured marker alone carries series identity. */
function legendText(value: string) {
  return <span className="chart-legend-text">{value}</span>;
}

/**
 * Vertical bars for one series. The axis labels identify the bars, so one colour suffices.
 * Counts are the default; pass `format` for measures with decimals, such as PR-AUC.
 */
export function CategoryBars({
  data,
  valueLabel,
  format,
}: {
  data: CategoryDatum[];
  valueLabel: string;
  format?: (value: number) => string;
}) {
  const formatValue = format ?? formatCount;
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={formatValue} allowDecimals={format !== undefined} />
        <Tooltip formatter={(value: number) => [formatValue(value), valueLabel]} />
        <Bar dataKey="value" name={valueLabel} fill={SERIES_PRIMARY} radius={[4, 4, 0, 0]} maxBarSize={56} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface PairDatum {
  label: string;
  first: number;
  second: number;
}

/** Two series measured in the same unit, side by side, with a legend. */
export function PairedBars({ data, firstLabel, secondLabel }: { data: PairDatum[]; firstLabel: string; secondLabel: string }) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }} barGap={2}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={formatCount} allowDecimals={false} />
        <Tooltip formatter={(value: number) => formatCount(value)} />
        <Legend formatter={legendText} />
        <Bar dataKey="first" name={firstLabel} fill={SERIES_PRIMARY} radius={[4, 4, 0, 0]} maxBarSize={40} />
        <Bar dataKey="second" name={secondLabel} fill={SERIES_SECONDARY} radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface TrendDatum {
  x: number;
  y: number;
}

/** One series over a numeric axis, such as simulated day. */
export function TrendLine({ data, xLabel, yLabel }: { data: TrendDatum[]; xLabel: string; yLabel: string }) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="x"
          type="number"
          domain={["dataMin", "dataMax"]}
          allowDecimals={false}
          tick={AXIS_TICK}
          label={{ value: xLabel, position: "insideBottom", offset: -12, fill: AXIS_TEXT, fontSize: 12 }}
        />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={formatCount} allowDecimals={false} />
        <Tooltip formatter={(value: number) => [formatCount(value), yLabel]} labelFormatter={(x) => `${xLabel} ${x}`} />
        <Line type="monotone" dataKey="y" name={yLabel} stroke={SERIES_PRIMARY} strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export interface ContributionDatum {
  label: string;
  value: number;
}

/** Horizontal bars either side of zero: red raises the score, blue lowers it. */
export function ContributionBars({ data }: { data: ContributionDatum[] }) {
  const height = Math.max(160, data.length * 36);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS_TICK} tickFormatter={(value: number) => value.toFixed(1)} />
        <YAxis type="category" dataKey="label" width={170} tick={AXIS_TICK} tickLine={false} />
        <ReferenceLine x={0} stroke={REFERENCE} />
        <Tooltip formatter={(value: number) => [value.toFixed(3), "Contribution (log-odds)"]} />
        <Bar dataKey="value" radius={4} maxBarSize={22}>
          {data.map((datum) => (
            <Cell key={datum.label} fill={datum.value >= 0 ? RAISES_SCORE : LOWERS_SCORE} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface CurveSeries {
  name: string;
  points: { x: number; y: number }[];
}

const SERIES_COLOURS = [SERIES_PRIMARY, SERIES_SECONDARY];
const PROPORTION_TICKS = [0, 0.2, 0.4, 0.6, 0.8, 1];
const LOG_TICKS = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1];

/**
 * Up to two curves on shared numeric axes, such as precision against recall. Two is the limit
 * because only that pair of colours passed the palette checks together.
 */
export function CurveChart({
  series,
  xLabel,
  yLabel,
  logX = false,
}: {
  series: CurveSeries[];
  xLabel: string;
  yLabel: string;
  logX?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT + 40}>
      <LineChart margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis
          type="number"
          dataKey="x"
          scale={logX ? "log" : "auto"}
          domain={logX ? [LOG_TICKS[0], 1] : [0, 1]}
          ticks={logX ? LOG_TICKS : PROPORTION_TICKS}
          allowDataOverflow={logX}
          tick={AXIS_TICK}
          tickFormatter={(value: number) => (logX ? value.toExponential(0) : value.toFixed(1))}
          label={{ value: xLabel, position: "insideBottom", offset: -14, fill: AXIS_TEXT, fontSize: 12 }}
        />
        <YAxis
          type="number"
          domain={[0, 1]}
          ticks={PROPORTION_TICKS}
          tick={AXIS_TICK}
          tickFormatter={(value: number) => value.toFixed(1)}
          label={{ value: yLabel, angle: -90, position: "insideLeft", fill: AXIS_TEXT, fontSize: 12 }}
        />
        <Tooltip formatter={(value: number) => value.toFixed(4)} labelFormatter={(x: number) => `${xLabel} ${Number(x).toPrecision(3)}`} />
        <Legend verticalAlign="top" formatter={legendText} />
        {series.slice(0, 2).map((curve, index) => (
          <Line
            key={curve.name}
            data={curve.points}
            dataKey="y"
            name={curve.name}
            stroke={SERIES_COLOURS[index]}
            strokeWidth={2}
            dot={false}
            type="linear"
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** A single headline figure with a label and an optional note. */
export function StatTile({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="card stat-tile">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {note ? <span className="muted small">{note}</span> : null}
    </div>
  );
}
