import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Table2, Braces } from "lucide-react";

interface BlockListProps {
  blocks: Record<string, unknown>[][];
  rotationState: number;
  /** Render blocks in logical read order (starting at rotation) instead of storage order. */
  logicalOrder: boolean;
}

type FlatRecord = Record<string, unknown>;

function isFlatRecord(record: Record<string, unknown>): boolean {
  return Object.values(record).every(
    (value) => value === null || ["string", "number", "boolean"].includes(typeof value),
  );
}

function collectColumns(records: FlatRecord[]): string[] {
  const columns = new Set<string>();
  for (const record of records) Object.keys(record).forEach((key) => columns.add(key));
  return [...columns].sort();
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function RecordTable({ records }: { records: FlatRecord[] }) {
  const columns = collectColumns(records);
  return (
    <div className="overflow-x-auto nice-scroll rounded-lg border border-slate-700/60">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(record[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Accordion listing the physical blocks of a container. */
export function BlockList({ blocks, rotationState, logicalOrder }: BlockListProps) {
  const [open, setOpen] = useState<Set<number>>(() => new Set([0]));
  const order = useMemo(() => {
    const indices = blocks.map((_, index) => index);
    if (!logicalOrder || indices.length === 0) return indices;
    return [...indices.slice(rotationState), ...indices.slice(0, rotationState)];
  }, [blocks, logicalOrder, rotationState]);

  const toggle = (index: number) => {
    setOpen((previous) => {
      const next = new Set(previous);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  if (blocks.length === 0) {
    return <div className="text-xs text-slate-500">No blocks.</div>;
  }

  return (
    <div className="space-y-1.5">
      {order.map((blockIndex) => {
        const block = blocks[blockIndex];
        const expanded = open.has(blockIndex);
        const flat = block.length > 0 && block.every(isFlatRecord);
        const isCurrent = blockIndex === rotationState;
        return (
          <div
            key={blockIndex}
            className={`overflow-hidden rounded-lg border transition-colors ${
              isCurrent ? "border-cyan-500/45 bg-cyan-500/5" : "border-slate-700/60 bg-slate-900/40"
            }`}
          >
            <button
              type="button"
              onClick={() => toggle(blockIndex)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left"
              aria-expanded={expanded}
            >
              {expanded ? (
                <ChevronDown size={14} className="text-slate-500" />
              ) : (
                <ChevronRight size={14} className="text-slate-500" />
              )}
              <span className="font-mono2 text-[0.72rem] font-bold text-slate-200">
                BLOCK {blockIndex}
              </span>
              {isCurrent ? <span className="chip chip-info !py-0 !text-[0.58rem]">current</span> : null}
              <span className="ml-auto text-[0.65rem] text-slate-500">
                {block.length} record{block.length === 1 ? "" : "s"}
              </span>
              {flat && block.length > 0 ? (
                <Table2 size={12} className="text-slate-500" aria-label="Tabular data" />
              ) : (
                <Braces size={12} className="text-slate-500" aria-label="Nested data" />
              )}
            </button>
            {expanded ? (
              <div className="border-t border-slate-700/60 p-2">
                {block.length === 0 ? (
                  <div className="py-2 text-center text-[0.7rem] text-slate-500">
                    Empty block — still addressable in the rotation
                  </div>
                ) : flat ? (
                  <RecordTable records={block} />
                ) : (
                  <div className="max-h-52 space-y-1 overflow-auto nice-scroll">
                    {block.map((record, recordIndex) => (
                      <pre
                        key={recordIndex}
                        className="rounded-md bg-slate-950/70 p-2 font-mono2 text-[0.68rem] text-emerald-100/90"
                      >
                        {JSON.stringify(record, null, 1)}
                      </pre>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
