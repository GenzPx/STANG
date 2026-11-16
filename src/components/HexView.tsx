import { useMemo } from "react";

interface HexViewProps {
  bytes: Uint8Array | null;
  highlight?: { offset: number; length: number } | null;
  maxRows?: number;
}

/** Classic hex + ASCII dump with an optional highlighted byte range. */
export function HexView({ bytes, highlight = null, maxRows = 320 }: HexViewProps) {
  const rows = useMemo(() => {
    if (!bytes) return [];
    const lines: { offset: number; hexCells: { text: string; hl: boolean }[]; ascii: { text: string; hl: boolean }[] }[] = [];
    const limit = Math.min(bytes.length, maxRows * 16);
    for (let rowStart = 0; rowStart < limit; rowStart += 16) {
      const rowEnd = Math.min(rowStart + 16, bytes.length);
      const hexCells: { text: string; hl: boolean }[] = [];
      const ascii: { text: string; hl: boolean }[] = [];
      for (let i = rowStart; i < rowEnd; i++) {
        const inHl =
          highlight !== null && i >= highlight.offset && i < highlight.offset + highlight.length;
        hexCells.push({ text: bytes[i].toString(16).padStart(2, "0"), hl: inHl });
        const ch = bytes[i];
        ascii.push({ text: ch >= 32 && ch < 127 ? String.fromCharCode(ch) : ".", hl: inHl });
      }
      lines.push({ offset: rowStart, hexCells, ascii });
    }
    return lines;
  }, [bytes, highlight, maxRows]);

  if (!bytes) {
    return (
      <div className="panel-inset flex h-40 items-center justify-center text-xs text-slate-500">
        Encode or load a container to see its raw bytes
      </div>
    );
  }

  const truncated = bytes.length > maxRows * 16;

  return (
    <div className="panel-inset max-h-80 overflow-auto nice-scroll p-3">
      <pre className="hexdump text-slate-300">
        {rows.map((row) => (
          // eslint-disable-next-line react/jsx-key
          <div key={row.offset} className="flex whitespace-pre">
            <span className="text-slate-500 select-none">
              {row.offset.toString(16).padStart(8, "0")}
            </span>
            <span>{"  "}</span>
            <span>
              {row.hexCells.map((cell, i) => (
                <span key={i} className={cell.hl ? "hl" : undefined}>
                  {cell.text}{" "}
                </span>
              ))}
              {row.hexCells.length < 16 ? " ".repeat((16 - row.hexCells.length) * 3) : null}
            </span>
            <span>{" "}</span>
            <span>
              {row.ascii.map((cell, i) => (
                <span key={i} className={cell.hl ? "hl" : undefined}>
                  {cell.text}
                </span>
              ))}
            </span>
          </div>
        ))}
        {truncated ? (
          <div className="text-slate-500">
            … {bytes.length - maxRows * 16} more bytes (preview truncated)
          </div>
        ) : null}
      </pre>
    </div>
  );
}
