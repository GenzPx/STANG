import type { StgSegment } from "../stg/codec";

const KIND_CLASS: Record<StgSegment["kind"], string> = {
  header: "seg-header",
  ext: "seg-ext",
  table: "seg-table",
  nonce: "seg-nonce",
  block: "seg-block",
  trailer: "seg-trailer",
};

function segmentClass(segment: StgSegment): string {
  if (segment.kind === "block" && segment.blockIndex !== undefined && segment.blockIndex % 2 === 1) {
    return "seg-block-alt";
  }
  return KIND_CLASS[segment.kind];
}

interface ByteMapProps {
  segments: StgSegment[];
  totalBytes: number;
  selectedKey: string | null;
  onSelect: (segment: StgSegment) => void;
}

/**
 * Proportional byte-map of a serialized container. Every segment of the file
 * is clickable and maps onto the hex view below it.
 */
export function ByteMap({ segments, totalBytes, selectedKey, onSelect }: ByteMapProps) {
  return (
    <div>
      <div className="bytemap nice-scroll" role="list" aria-label="Binary layout">
        {segments.map((segment) => (
          <button
            key={segment.key}
            role="listitem"
            type="button"
            className={`bytemap-segment ${segmentClass(segment)}`}
            style={{ flexGrow: segment.length, flexBasis: 0 }}
            data-selected={segment.key === selectedKey}
            onClick={() => onSelect(segment)}
            title={`${segment.label} — ${segment.length} B @ 0x${segment.offset.toString(16)}`}
            aria-label={`${segment.label}, ${segment.length} bytes at offset ${segment.offset}`}
          />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-[0.65rem] text-slate-400">
        {segments.map((segment) => (
          <button
            key={segment.key}
            type="button"
            onClick={() => onSelect(segment)}
            className="flex items-center gap-1.5 hover:text-slate-200 transition-colors"
          >
            <span className={`inline-block h-2.5 w-2.5 rounded-[3px] ${segmentClass(segment)}`} />
            <span className="font-mono2">
              {segment.label} <span className="text-slate-500">({segment.length} B)</span>
            </span>
          </button>
        ))}
      </div>
      <div className="mt-1 text-[0.62rem] uppercase tracking-wider text-slate-500">
        {totalBytes.toLocaleString()} bytes total — offsets shown in hex
      </div>
    </div>
  );
}
