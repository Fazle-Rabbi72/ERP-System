import type * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";

export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps): React.JSX.Element {
  return (
    <div role="status" aria-label="Loading data" className="space-y-3">
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${String(columns)}, minmax(0, 1fr))` }}>
        {Array.from({ length: columns }).map((_, idx) => (
          <Skeleton key={`hdr-${String(idx)}`} className="h-5 w-3/4" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={`row-${String(rowIdx)}`}
          className="grid gap-3 border-t border-border pt-3"
          style={{ gridTemplateColumns: `repeat(${String(columns)}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }).map((__, colIdx) => (
            <Skeleton key={`cell-${String(rowIdx)}-${String(colIdx)}`} className="h-4 w-full" />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  );
}
