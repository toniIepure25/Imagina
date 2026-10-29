"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

export default function VirtualList<T>({
  items,
  rowHeight,
  height,
  renderRow,
  getKey,
  ariaLabel,
  className = "",
  overscan = 4,
}: {
  items: T[];
  rowHeight: number;
  height: number;
  renderRow: (item: T, index: number) => ReactNode;
  getKey: (item: T, index: number) => string;
  ariaLabel: string;
  className?: string;
  overscan?: number;
}) {
  const [scrollTop, setScrollTop] = useState(0);
  const frame = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (frame.current !== null) window.cancelAnimationFrame(frame.current);
    },
    [],
  );

  const visibleWindow = useMemo(() => {
    const visibleCount = Math.ceil(height / rowHeight);
    const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const end = Math.min(items.length, start + visibleCount + overscan * 2);
    return { start, end };
  }, [height, items.length, overscan, rowHeight, scrollTop]);

  return (
    <div
      role="list"
      aria-label={ariaLabel}
      className={`overflow-auto ${className}`}
      style={{ height }}
      onScroll={(event) => {
        const next = event.currentTarget.scrollTop;
        if (frame.current !== null) window.cancelAnimationFrame(frame.current);
        frame.current = window.requestAnimationFrame(() => setScrollTop(next));
      }}
    >
      <div className="relative" style={{ height: items.length * rowHeight }}>
        {items.slice(visibleWindow.start, visibleWindow.end).map((item, offset) => {
          const index = visibleWindow.start + offset;
          return (
            <div
              key={getKey(item, index)}
              role="listitem"
              aria-setsize={items.length}
              aria-posinset={index + 1}
              className="absolute inset-x-0"
              style={{ height: rowHeight, transform: `translateY(${index * rowHeight}px)` }}
            >
              {renderRow(item, index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
