/**
 * A table with a caption, an empty state and previous and next paging.
 */
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { formatCount } from "../utils/format";
import { EmptyState } from "./feedback";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  numeric?: boolean;
}

/**
 * The horizontally scrolling area around a wide table. It takes keyboard focus, so people who
 * cannot use a mouse or touch can scroll it with the arrow keys (WCAG 2.1.1), and it is the
 * containing block for visually hidden text inside the table, which otherwise widened the page.
 */
export function TableScroll({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="table-wrap" role="group" aria-label={`${label}, scrollable table`} tabIndex={0}>
      {children}
    </div>
  );
}

export interface DataTableProps<T> {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle: string;
  emptyMessage?: string;
  onRowSelect?: (row: T) => void;
  selectedKey?: string | null;
}

export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  emptyTitle,
  emptyMessage,
  onRowSelect,
  selectedKey,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle}>{emptyMessage}</EmptyState>;
  }
  return (
    <TableScroll label={caption}>
      <table className="data-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={column.numeric ? "numeric" : undefined}>
                {column.header}
              </th>
            ))}
            {onRowSelect ? <th scope="col"><span className="visually-hidden">Open</span></th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = rowKey(row);
            return (
              <tr key={key} className={key === selectedKey ? "selected" : undefined}>
                {columns.map((column) => (
                  <td key={column.key} className={column.numeric ? "numeric" : undefined}>
                    {column.render(row)}
                  </td>
                ))}
                {onRowSelect ? (
                  <td>
                    <button type="button" className="button link" onClick={() => onRowSelect(row)}>
                      Open
                    </button>
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </TableScroll>
  );
}

export interface PagerProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export function Pager({ total, limit, offset, onChange }: PagerProps) {
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + limit, total);
  return (
    <nav className="pager" aria-label="Pages">
      <span>
        {formatCount(first)}–{formatCount(last)} of {formatCount(total)}
      </span>
      <button
        type="button"
        className="button secondary icon"
        onClick={() => onChange(Math.max(offset - limit, 0))}
        disabled={offset === 0}
        aria-label="Previous page"
      >
        <ChevronLeft aria-hidden="true" />
      </button>
      <button
        type="button"
        className="button secondary icon"
        onClick={() => onChange(offset + limit)}
        disabled={offset + limit >= total}
        aria-label="Next page"
      >
        <ChevronRight aria-hidden="true" />
      </button>
    </nav>
  );
}
