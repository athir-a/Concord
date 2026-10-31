import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useDebounced } from "../lib/hooks";
import { Button } from "./Button";
import { EmptyState, ErrorState, Skeleton } from "./Layout";

const PAGE_SIZE = 25;

function SortHeader({ column, ordering, onSort }) {
  const active = ordering === column.sort || ordering === `-${column.sort}`;
  const descending = ordering === `-${column.sort}`;
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 font-medium hover:text-ink"
      onClick={() => onSort(active && !descending ? `-${column.sort}` : column.sort)}
    >
      {column.header}
      {active && (descending ? <ArrowDown size={13} aria-label="sorted descending" /> : <ArrowUp size={13} aria-label="sorted ascending" />)}
    </button>
  );
}

/** Tables scroll sideways inside themselves on small screens, never the whole page. */
export function DataTable({ columns, query, empty, ordering, onSort, onPage, rowKey = (row) => row.id }) {
  const { data, isLoading, error, refetch, isPlaceholderData } = query;
  if (error) return <ErrorState error={error} retry={refetch} />;

  const rows = data?.results ?? [];
  const page = query.page ?? 1;
  const total = data?.count ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (!isLoading && total === 0) return empty ?? <EmptyState title="Nothing here yet" />;

  return (
    <>
      <div className={`overflow-x-auto transition-opacity duration-150 ${isPlaceholderData ? "opacity-60" : ""}`}>
        <table className="w-full min-w-[640px] text-left">
          <thead>
            <tr className="border-b border-line text-[13px] text-ink-muted">
              {columns.map((column) => (
                <th key={column.header} scope="col" className={`px-4 py-2.5 font-medium whitespace-nowrap ${column.right ? "text-right" : ""}`}>
                  {column.sort && onSort ? <SortHeader {...{ column, ordering, onSort }} /> : column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? [0, 1, 2, 3, 4].map((i) => (
                  <tr key={i} className="border-b border-line last:border-0">
                    {columns.map((column) => (
                      <td key={column.header} className="px-4 py-3"><Skeleton className="h-4 w-full" /></td>
                    ))}
                  </tr>
                ))
              : rows.map((row) => (
                  <tr key={rowKey(row)} className="border-b border-line transition-colors duration-150 last:border-0 hover:bg-canvas/60">
                    {columns.map((column) => (
                      <td key={column.header} className={`px-4 py-3 ${column.right ? "tabular text-right" : ""} ${column.nowrap === false ? "" : "whitespace-nowrap"}`}>
                        {column.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
      {!isLoading && pages > 1 && (
        <nav aria-label="Pages" className="flex items-center justify-between gap-3 border-t border-line px-4 py-2.5 text-[13px] text-ink-muted">
          <span className="tabular">{total.toLocaleString("en-IN")} results</span>
          <span className="flex items-center gap-1">
            <Button variant="ghost" className="h-8 px-2" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}>
              <ChevronLeft size={16} aria-hidden="true" />
            </Button>
            <span className="tabular px-1">Page {page} of {pages.toLocaleString("en-IN")}</span>
            <Button variant="ghost" className="h-8 px-2" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}>
              <ChevronRight size={16} aria-hidden="true" />
            </Button>
          </span>
        </nav>
      )}
    </>
  );
}

export function SearchBox({ value, onChange, placeholder = "Search" }) {
  const [text, setText] = useState(value ?? "");
  const debounced = useDebounced(text);
  useEffect(() => {
    if (debounced !== (value ?? "")) onChange(debounced);
    // Only react to typing, not to the URL changing underneath.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);
  return (
    <div className="relative min-w-48 flex-1 sm:max-w-xs">
      <Search size={15} aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-faint" />
      <input
        type="search"
        aria-label={placeholder}
        placeholder={placeholder}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="h-9 w-full rounded-md border border-line-strong bg-surface pr-3 pl-8.5"
      />
    </div>
  );
}

export function FilterSelect({ label, value, onChange, options }) {
  return (
    <select
      aria-label={label}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 rounded-md border border-line-strong bg-surface px-2.5"
    >
      <option value="">{label}: all</option>
      {options.map(([optionValue, optionLabel]) => (
        <option key={optionValue} value={optionValue}>{optionLabel}</option>
      ))}
    </select>
  );
}

export function TableToolbar({ children }) {
  return <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">{children}</div>;
}

/** Wires a useListPage result into DataTable. */
export function listProps(list) {
  return {
    query: list,
    ordering: list.params.ordering,
    onSort: (value) => list.setParam("ordering", value),
    onPage: (value) => list.setParam("page", String(value)),
  };
}
