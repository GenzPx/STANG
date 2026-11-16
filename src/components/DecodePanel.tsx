import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  Copy,
  FileUp,
  FolderOpen,
  KeyRound,
  Lock,
  ScanSearch,
  ShieldCheck,
  ShieldQuestion,
  Trash2,
  TriangleAlert,
  Wand2,
} from "lucide-react";
import {
  fromHex,
  parseStg,
  serializeStg,
  sniffHeader,
  type HeaderSummary,
  type ParsedContainer,
  type StgSegment,
} from "../stg/codec";
import { SAMPLE_DATASETS } from "../stg/samples";
import { ByteMap } from "./ByteMap";
import { HexView } from "./HexView";
import { BlockList } from "./BlockList";

type LoadState =
  | { status: "idle" }
  | { status: "ready"; bytes: Uint8Array; name: string }
  | {
      status: "decoded";
      bytes: Uint8Array;
      name: string;
      parsed: ParsedContainer;
    }
  | { status: "error"; bytes: Uint8Array | null; name: string; message: string };

const SAMPLE_PASSPHRASE = "secret-stang-key";

function tryParseBase64(text: string): Uint8Array | null {
  const clean = text.trim().replace(/\s+/g, "");
  if (!clean || !/^[A-Za-z0-9+/]+={0,2}$/.test(clean) || clean.length % 4 !== 0) return null;
  try {
    const binary = atob(clean);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  } catch {
    return null;
  }
}

export function DecodePanel() {
  const [state, setState] = useState<LoadState>({ status: "idle" });
  const [pasteText, setPasteText] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [integrityKey, setIntegrityKey] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState<StgSegment | null>(null);
  const [copied, setCopied] = useState(false);
  const [logicalOrder, setLogicalOrder] = useState(false);
  const [busy, setBusy] = useState(false);

  const header: HeaderSummary | null = useMemo(() => {
    if (state.status === "idle") return null;
    return state.bytes ? sniffHeader(state.bytes) : null;
  }, [state]);

  const loadBytes = useCallback((bytes: Uint8Array, name: string) => {
    setSelectedSegment(null);
    setState({ status: "ready", bytes, name });
  }, []);

  const onFile = useCallback(
    (file: File) => {
      file.arrayBuffer().then((buffer) => loadBytes(new Uint8Array(buffer), file.name));
    },
    [loadBytes],
  );

  const loadFromPaste = () => {
    const text = pasteText.trim();
    if (!text) return;
    // Hex first, then base64.
    try {
      const bytes = fromHex(text);
      loadBytes(bytes, "pasted-hex.stg");
      setPasteText("");
      return;
    } catch {
      /* not hex */
    }
    const b64 = tryParseBase64(text);
    if (b64) {
      loadBytes(b64, "pasted-base64.stg");
      setPasteText("");
      return;
    }
    setState({
      status: "error",
      bytes: null,
      name: "paste",
      message: "Could not parse the pasted payload as hex or base64.",
    });
  };

  const loadSample = useCallback(
    async (kind: "plain" | "encrypted" | "legacy") => {
      setBusy(true);
      try {
        const records = SAMPLE_DATASETS[2].records; // Mixed profiles — shows off types
        if (kind === "legacy") {
          const bytes = await serializeStg({ records, blockCount: 4, rotationState: 2, format: "stg1" });
          loadBytes(bytes, "sample-legacy.stg");
        } else if (kind === "encrypted") {
          const bytes = await serializeStg({
            records,
            blockCount: 4,
            rotationState: 1,
            format: "stg2",
            compress: true,
            passphrase: SAMPLE_PASSPHRASE,
          });
          loadBytes(bytes, "sample-encrypted.stg");
        } else {
          const bytes = await serializeStg({
            records,
            blockCount: 4,
            rotationState: 1,
            format: "stg2",
            compress: true,
          });
          loadBytes(bytes, "sample-plain.stg");
        }
      } finally {
        setBusy(false);
      }
    },
    [loadBytes],
  );

  const decode = useCallback(async () => {
    if (state.status !== "ready") return;
    const bytes = state.bytes;
    const name = state.name;
    const sniffed = sniffHeader(bytes);
    setBusy(true);
    try {
      const parsed = await parseStg(bytes, {
        passphrase: sniffed?.encrypted ? passphrase : undefined,
        integrityKey: sniffed?.hmac ? integrityKey : undefined,
      });
      setSelectedSegment(null);
      setState({ status: "decoded", bytes, name, parsed });
    } catch (err) {
      setState({
        status: "error",
        bytes,
        name,
        message: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  }, [state, passphrase, integrityKey]);

  // Auto-decode containers that need no credentials.
  useEffect(() => {
    if (state.status === "ready") {
      const sniffed = sniffHeader(state.bytes);
      if (sniffed && !sniffed.encrypted && !sniffed.hmac) {
        void decode();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.status]);

  const downloadReencoded = () => {
    if (state.status !== "decoded") return;
    const { bytes } = state;
    const blob = new Blob([bytes.slice().buffer], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = state.name.replace(/(\.stg)?$/, ".reserialized.stg");
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const copyDecoded = async () => {
    if (state.status !== "decoded") return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(state.parsed.records, null, 2));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard unavailable */
    }
  };

  const reset = () => {
    setState({ status: "idle" });
    setSelectedSegment(null);
    setPassphrase("");
    setIntegrityKey("");
  };

  const name = state.status !== "idle" ? state.name : null;
  const needsPassphrase = header?.encrypted ?? false;
  const needsKey = header?.hmac ?? false;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(430px,6fr)_7fr]">
      {/* ------------------------------- Input column ------------------------------ */}
      <section className="panel p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ScanSearch size={16} className="text-cyan-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">LOAD A .STG FILE</h2>
          </div>
          {state.status !== "idle" ? (
            <button className="btn btn-ghost btn-sm" onClick={reset}>
              <Trash2 size={12} /> clear
            </button>
          ) : null}
        </div>

        <label
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            const file = event.dataTransfer.files?.[0];
            if (file) onFile(file);
          }}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors ${
            dragOver
              ? "border-cyan-400/70 bg-cyan-400/10"
              : "border-slate-700 bg-slate-900/40 hover:border-slate-600"
          }`}
        >
          <input
            type="file"
            accept=".stg,application/octet-stream"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onFile(file);
              event.target.value = "";
            }}
          />
          <FileUp size={26} className="text-slate-500" />
          <div className="text-[0.8rem] font-semibold text-slate-300">
            Drop a <span className="font-mono2 text-cyan-300">.stg</span> file here, or click to browse
          </div>
          <div className="text-[0.62rem] text-slate-500">
            Parsed entirely in your browser — nothing leaves this machine
          </div>
        </label>

        <div className="mt-3">
          <span className="field-label">Or paste hex / base64</span>
          <textarea
            className="textarea h-20 text-[0.68rem]"
            placeholder="5354 4732 ... or 535447MiAgAA..."
            value={pasteText}
            onChange={(event) => setPasteText(event.target.value)}
            spellCheck={false}
          />
          <div className="mt-1.5 flex items-center gap-2">
            <button className="btn btn-ghost btn-sm" onClick={loadFromPaste} disabled={!pasteText.trim()}>
              <FolderOpen size={13} /> load pasted bytes
            </button>
            <span className="text-[0.62rem] text-slate-500">
              {pasteText.trim() ? `${pasteText.trim().replace(/\s+/g, "").length.toLocaleString()} chars` : ""}
            </span>
          </div>
        </div>

        <div className="mt-3">
          <span className="field-label">Sample containers</span>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => loadSample("plain")}>
              <Wand2 size={12} /> STG2 plain
            </button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => loadSample("encrypted")}>
              <Lock size={12} /> STG2 encrypted
            </button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => loadSample("legacy")}>
              <Wand2 size={12} /> STG1 legacy
            </button>
          </div>
          <p className="mt-1 text-[0.62rem] text-slate-500">
            Encrypted sample uses passphrase{" "}
            <code className="rounded bg-slate-800 px-1 font-mono2 text-amber-300">{SAMPLE_PASSPHRASE}</code>
          </p>
        </div>

        {name ? (
          <div className="panel-inset mt-3 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2 text-[0.72rem]">
              <span className="font-mono2 font-bold text-slate-200">{name}</span>
              {header ? (
                <>
                  <span className="chip chip-info">
                    STG<b>{header.version}</b>
                  </span>
                  <span className="chip">
                    blocks <b>{header.blockCount || "?"}</b>
                  </span>
                  <span className="chip">
                    rotation <b>{header.rotationState}</b>
                  </span>
                  {header.flagNames.map((flag) => (
                    <span key={flag} className="chip chip-violet">{flag}</span>
                  ))}
                  <span className="chip">{header.sizeBytes.toLocaleString()} B</span>
                </>
              ) : (
                <span className="chip chip-bad">unrecognized magic</span>
              )}
            </div>
          </div>
        ) : null}

        {needsPassphrase ? (
          <div className="mt-3 rounded-xl border border-violet-400/30 bg-violet-400/5 p-3">
            <label htmlFor="decode-pass" className="field-label flex items-center gap-1.5">
              <Lock size={11} /> This container is encrypted — passphrase required
            </label>
            <div className="flex gap-2">
              <input
                id="decode-pass"
                type="password"
                className="input font-mono2"
                placeholder="PBKDF2 passphrase"
                value={passphrase}
                onChange={(event) => setPassphrase(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && decode()}
                autoComplete="off"
              />
              <button className="btn btn-primary" onClick={decode} disabled={busy}>
                <KeyRound size={14} /> Unlock
              </button>
            </div>
          </div>
        ) : null}

        {needsKey ? (
          <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-3">
            <label htmlFor="decode-key" className="field-label flex items-center gap-1.5">
              <ShieldQuestion size={11} /> HMAC integrity key required
            </label>
            <div className="flex gap-2">
              <input
                id="decode-key"
                type="password"
                className="input font-mono2"
                placeholder="integrity key"
                value={integrityKey}
                onChange={(event) => setIntegrityKey(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && decode()}
                autoComplete="off"
              />
              <button className="btn btn-primary" onClick={decode} disabled={busy}>
                <KeyRound size={14} /> Verify
              </button>
            </div>
          </div>
        ) : null}

        {state.status === "error" ? (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-400/40 bg-rose-400/10 px-3 py-2 text-[0.72rem] text-rose-300">
            <TriangleAlert size={14} className="mt-0.5 flex-none" />
            <span>{state.message}</span>
          </div>
        ) : null}
      </section>

      {/* ------------------------------ Result column ------------------------------ */}
      <section className="panel flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">DECODED CONTENT</h2>
          </div>
          {state.status === "decoded" ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="chip chip-ok">
                <ShieldCheck size={10} />{" "}
                {state.parsed.integrity === "aead"
                  ? "AEAD authenticated"
                  : state.parsed.integrity === "hmac"
                    ? "HMAC verified"
                    : "SHA-256 valid"}
              </span>
              <button className="btn btn-ghost btn-sm" onClick={downloadReencoded}>
                <FileUp size={12} /> re-save .stg
              </button>
              <button className="btn btn-ghost btn-sm" onClick={copyDecoded}>
                {copied ? <Check size={12} /> : <Copy size={12} />} copy JSON
              </button>
            </div>
          ) : null}
        </div>

        {state.status !== "decoded" ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-700/70 py-14 text-center">
            <ScanSearch size={52} className="text-slate-700" strokeWidth={1.4} />
            <div className="text-sm font-semibold text-slate-300">No container decoded yet</div>
            <p className="max-w-xs text-[0.72rem] leading-relaxed text-slate-500">
              Drop a file or load a sample on the left. Encrypted containers ask for their
              passphrase before anything is decrypted.
            </p>
          </div>
        ) : (
          <>
            <ByteMap
              segments={state.parsed.segments}
              totalBytes={state.bytes.length}
              selectedKey={selectedSegment?.key ?? null}
              onSelect={setSelectedSegment}
            />
            {selectedSegment ? (
              <div className="panel-inset flex flex-wrap items-center gap-x-6 gap-y-1 px-3 py-2 text-[0.7rem]">
                <span className="font-bold text-cyan-300">{selectedSegment.label}</span>
                <span className="font-mono2 text-slate-400">
                  0x{selectedSegment.offset.toString(16).padStart(4, "0")}…0x
                  {(selectedSegment.offset + selectedSegment.length - 1).toString(16).padStart(4, "0")}
                </span>
                <span className="font-mono2 text-slate-400">{selectedSegment.length} B</span>
                <span className="text-slate-400">{selectedSegment.detail}</span>
              </div>
            ) : null}
            <HexView
              bytes={state.bytes}
              highlight={
                selectedSegment
                  ? { offset: selectedSegment.offset, length: selectedSegment.length }
                  : null
              }
            />
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="field-label !mb-0">
                  Records ({state.parsed.records.length})
                </span>
                <button
                  className="flex items-center gap-1.5 text-[0.65rem] font-semibold text-slate-400 hover:text-slate-200"
                  onClick={() => setLogicalOrder((v) => !v)}
                >
                  <span className="toggle scale-[0.72]" data-on={logicalOrder} aria-hidden="true" />
                  logical read order
                </button>
              </div>
              <BlockList
                blocks={state.parsed.blocks}
                rotationState={state.parsed.rotationState}
                logicalOrder={logicalOrder}
              />
            </div>
            <div>
              <span className="field-label">Decoded JSON (canonical)</span>
              <textarea
                readOnly
                className="textarea h-36 text-[0.68rem]"
                value={JSON.stringify(state.parsed.records, null, 1)}
                aria-label="Decoded JSON records"
              />
            </div>
          </>
        )}
      </section>
    </div>
  );
}
