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

/** Vertical bars for one series. The axis labels identify the bars, so one colour suffices. */
export function CategoryBars({ data, valueLabel }: { data: CategoryDatum[]; valueLabel: string }) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={formatCount} allowDecimals={false} />
        <Tooltip formatter={(value: number) => [formatCount(value), valueLabel]} />
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
        <Legend />
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
