import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Braces,
  Check,
  Copy,
  Dices,
  Download,
  FileJson2,
  Lock,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Zap,
} from "lucide-react";
import {
  parseStg,
  serializeStg,
  toHex,
  type ParsedContainer,
  type StgFormat,
  type StgSegment,
} from "../stg/codec";
import { SAMPLE_DATASETS } from "../stg/samples";
import { ByteMap } from "./ByteMap";
import { HexView } from "./HexView";
import { RotationDial } from "./RotationDial";
import { BlockList } from "./BlockList";

interface EncodeResult {
  bytes: Uint8Array;
  parsed: ParsedContainer;
  jsonSize: number;
  elapsedMs: number;
}

function passphraseStrength(passphrase: string): { score: number; label: string; hint: string } {
  if (!passphrase) return { score: 0, label: "empty", hint: "type a passphrase" };
  let score = 0;
  if (passphrase.length >= 8) score++;
  if (passphrase.length >= 14) score++;
  if (/[A-Z]/.test(passphrase) && /[a-z]/.test(passphrase)) score++;
  if (/[0-9]/.test(passphrase) || /[^A-Za-z0-9]/.test(passphrase)) score++;
  const labels = ["very weak", "weak", "fair", "strong", "excellent"];
  const hints = [
    "use 14+ characters",
    "add mixed case / digits",
    "add symbols",
    "looks good",
    "great entropy",
  ];
  return { score, label: labels[score], hint: hints[score] };
}

function randomPassphrase(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

function Toggle({
  on,
  onToggle,
  label,
  hint,
  disabled = false,
}: {
  on: boolean;
  onToggle: () => void;
  label: string;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={`flex w-full items-center justify-between gap-3 rounded-lg border border-slate-700/60 bg-slate-900/40 px-3 py-2 text-left transition-opacity ${
        disabled ? "opacity-40" : "hover:border-slate-600"
      }`}
      aria-pressed={on}
    >
      <span>
        <span className="block text-[0.78rem] font-semibold text-slate-200">{label}</span>
        {hint ? <span className="block text-[0.62rem] text-slate-500">{hint}</span> : null}
      </span>
      <span className="toggle" data-on={on} aria-hidden="true" />
    </button>
  );
}

export function EncodePanel() {
  const [sampleId, setSampleId] = useState("orders");
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(SAMPLE_DATASETS[0].records, null, 2),
  );
  const [blockCount, setBlockCount] = useState(4);
  const [rotation, setRotation] = useState(0);
  const [format, setFormat] = useState<StgFormat>("stg2");
  const [compress, setCompress] = useState(true);
  const [encrypt, setEncrypt] = useState(false);
  const [hmacIntegrity, setHmacIntegrity] = useState(false);
  const [passphrase, setPassphrase] = useState("");
  const [integrityKey, setIntegrityKey] = useState("");
  const [result, setResult] = useState<EncodeResult | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<StgSegment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"hex" | "json" | null>(null);
  const [logicalOrder, setLogicalOrder] = useState(false);
  const [busy, setBusy] = useState(false);

  const validity = useMemo(() => {
    try {
      const parsed = JSON.parse(jsonText) as unknown;
      if (Array.isArray(parsed)) {
        if (!parsed.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
          return { ok: false as const, message: "Array must contain only objects." };
        }
        return { ok: true as const, records: parsed as Record<string, unknown>[] };
      }
      if (parsed && typeof parsed === "object") {
        return { ok: true as const, records: [parsed as Record<string, unknown>] };
      }
      return { ok: false as const, message: "Root must be an object or an array of objects." };
    } catch (err) {
      return {
        ok: false as const,
        message: err instanceof Error ? err.message : "Invalid JSON",
      };
    }
  }, [jsonText]);

  const clampRotation = useCallback(
    (value: number, blocks: number) => ((value % blocks) + blocks) % blocks,
    [],
  );

  useEffect(() => {
    setRotation((current) => clampRotation(current, blockCount));
  }, [blockCount, clampRotation]);

  const loadSample = (id: string) => {
    setSampleId(id);
    const sample = SAMPLE_DATASETS.find((entry) => entry.id === id);
    if (sample) setJsonText(JSON.stringify(sample.records, null, 2));
  };

  const encode = useCallback(async () => {
    setError(null);
    if (!validity.ok) {
      setError(validity.message);
      return;
    }
    if (format === "stg1" && (compress || encrypt || hmacIntegrity)) {
      setError("STG1 cannot represent compression, encryption or HMAC. Switch to STG2.");
      return;
    }
    if (encrypt && !passphrase) {
      setError("Encryption is enabled — supply a passphrase.");
      return;
    }
    setBusy(true);
    try {
      const started = performance.now();
      const bytes = await serializeStg({
        records: validity.records,
        blockCount,
        rotationState: rotation,
        format,
        compress: format === "stg2" && compress,
        passphrase: format === "stg2" && encrypt ? passphrase : undefined,
        integrityKey: format === "stg2" && hmacIntegrity && !encrypt ? integrityKey : undefined,
      });
      const parsed = await parseStg(bytes, {
        passphrase: format === "stg2" && encrypt ? passphrase : undefined,
        integrityKey: format === "stg2" && hmacIntegrity && !encrypt ? integrityKey : undefined,
      });
      const elapsedMs = performance.now() - started;
      setResult({
        bytes,
        parsed,
        jsonSize: new TextEncoder().encode(jsonText).length,
        elapsedMs,
      });
      setSelectedSegment(null);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [validity, format, compress, encrypt, hmacIntegrity, passphrase, integrityKey, blockCount, rotation, jsonText]);

  const copy = async (what: "hex" | "json") => {
    if (!result) return;
    const text =
      what === "hex"
        ? toHex(result.bytes)
        : JSON.stringify(result.parsed.records, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      window.setTimeout(() => setCopied(null), 1400);
    } catch {
      /* clipboard unavailable */
    }
  };

  const download = () => {
    if (!result) return;
    const blob = new Blob([result.bytes.slice().buffer], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "container.stg";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const strength = passphraseStrength(passphrase);
  const v2 = format === "stg2";
  const ratio = result ? result.bytes.length / Math.max(1, result.jsonSize) : null;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(430px,6fr)_7fr]">
      {/* ------------------------------ Input column ------------------------------ */}
      <section className="panel p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileJson2 size={16} className="text-cyan-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">JSON INPUT</h2>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="sample" className="sr-only">Sample dataset</label>
            <select
              id="sample"
              className="select !w-auto !py-1.5 !text-[0.75rem]"
              value={sampleId}
              onChange={(event) => loadSample(event.target.value)}
            >
              {SAMPLE_DATASETS.map((sample) => (
                <option key={sample.id} value={sample.id}>
                  {sample.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <textarea
          className="textarea h-56 text-[0.72rem]"
          spellCheck={false}
          value={jsonText}
          onChange={(event) => setJsonText(event.target.value)}
          aria-label="JSON records to encode"
        />
        <div className="mt-1.5 flex h-5 items-center justify-between text-[0.68rem]">
          {validity.ok ? (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Check size={12} strokeWidth={3} /> valid — {validity.records.length} record
              {validity.records.length === 1 ? "" : "s"}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-rose-400">
              <TriangleAlert size={12} /> {validity.message}
            </span>
          )}
          <span className="font-mono2 text-slate-500">
            {new TextEncoder().encode(jsonText).length.toLocaleString()} B
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="col-span-2">
            <span className="field-label">Wire format</span>
            <div className="flex overflow-hidden rounded-lg border border-slate-700">
              {(["stg2", "stg1"] as StgFormat[]).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFormat(value)}
                  className={`flex-1 px-3 py-1.5 text-[0.72rem] font-bold tracking-wider transition-colors ${
                    format === value
                      ? "bg-cyan-400 text-slate-950"
                      : "bg-slate-900/60 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {value.toUpperCase()}
                  {value === "stg1" ? " · legacy" : " · current"}
                </button>
              ))}
            </div>
          </div>
          <div className="col-span-2 sm:col-span-2">
            <span className="field-label">Blocks — {blockCount}</span>
            <input
              type="range"
              min={1}
              max={16}
              value={blockCount}
              onChange={(event) => setBlockCount(Number(event.target.value))}
              className="mt-2.5 w-full accent-cyan-400"
              aria-label="Number of blocks"
            />
          </div>
        </div>

        <div className="mt-3 flex items-center gap-4 rounded-xl border border-slate-700/60 bg-slate-900/40 p-3">
          <RotationDial
            count={blockCount}
            value={rotation}
            onChange={setRotation}
            size={104}
          />
          <div className="min-w-0">
            <span className="field-label !mb-1">Rotation state</span>
            <div className="font-mono2 text-2xl font-bold text-cyan-300">
              {rotation}
              <span className="text-sm text-slate-500"> / {blockCount - 1}</span>
            </div>
            <p className="mt-1 text-[0.65rem] leading-snug text-slate-500">
              Logical only — the bytes never move. The decoder replays the rotation to read
              blocks starting at this position.
            </p>
            <div className="mt-1.5 flex gap-1.5">
              <button className="btn btn-ghost btn-sm !px-2" onClick={() => setRotation((r) => (r + 1) % blockCount)}>
                +1 turn
              </button>
              <button className="btn btn-ghost btn-sm !px-2" onClick={() => setRotation(0)}>
                reset
              </button>
            </div>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Toggle
            on={compress}
            onToggle={() => setCompress((v) => !v)}
            label="zlib compress blocks"
            hint="RFC 1950, level 9 — big win on text"
            disabled={!v2}
          />
          <Toggle
            on={encrypt}
            onToggle={() => setEncrypt((v) => !v)}
            label="Encrypt blocks"
            hint="PBKDF2 + HMAC-SHA256 counter mode"
            disabled={!v2}
          />
          <Toggle
            on={hmacIntegrity}
            onToggle={() => setHmacIntegrity((v) => !v)}
            label="HMAC integrity only"
            hint="Authenticate without hiding (no encryption)"
            disabled={!v2 || encrypt}
          />
          <div className="rounded-lg border border-slate-700/60 bg-slate-900/40 px-3 py-2 text-[0.62rem] leading-snug text-slate-500">
            <span className="mb-0.5 block font-bold uppercase tracking-wider text-slate-400">
              Format note
            </span>
            {v2
              ? "STG2 — header extension with schema, authenticated trailer, optional crypto."
              : "STG1 legacy — SHA-256 trailer, absolute block table. Read/write for compatibility."}
          </div>
        </div>

        {encrypt ? (
          <div className="mt-3 rounded-xl border border-violet-400/30 bg-violet-400/5 p-3">
            <div className="flex items-center justify-between gap-2">
              <label htmlFor="passphrase" className="field-label !mb-0 flex items-center gap-1.5">
                <Lock size={11} /> Passphrase
              </label>
              <button
                type="button"
                className="flex items-center gap-1 text-[0.65rem] font-semibold text-violet-300 hover:text-violet-200"
                onClick={() => setPassphrase(randomPassphrase())}
              >
                <Dices size={12} /> generate
              </button>
            </div>
            <input
              id="passphrase"
              type="text"
              className="input mt-1.5 font-mono2"
              placeholder="PBKDF2 input — 100 000 iterations"
              value={passphrase}
              onChange={(event) => setPassphrase(event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            <div className="mt-1.5 flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-rose-400 via-amber-400 to-emerald-400 transition-all duration-300"
                  style={{ width: `${(strength.score / 4) * 100}%` }}
                />
              </div>
              <span className="text-[0.62rem] font-semibold text-slate-400">
                {strength.label} · {strength.hint}
              </span>
            </div>
          </div>
        ) : null}

        {hmacIntegrity && !encrypt ? (
          <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-3">
            <label htmlFor="integrityKey" className="field-label flex items-center gap-1.5">
              <ShieldCheck size={11} /> Integrity key (raw string)
            </label>
            <input
              id="integrityKey"
              type="text"
              className="input font-mono2"
              placeholder="HMAC-SHA256 key material"
              value={integrityKey}
              onChange={(event) => setIntegrityKey(event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            <p className="mt-1 text-[0.62rem] text-slate-500">
              Anyone can read the data, but nobody can forge or flip it without this key.
            </p>
          </div>
        ) : null}

        {error ? (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-400/40 bg-rose-400/10 px-3 py-2 text-[0.72rem] text-rose-300">
            <TriangleAlert size={14} className="mt-0.5 flex-none" />
            <span>{error}</span>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button className="btn btn-primary" onClick={encode} disabled={busy || !validity.ok}>
            <Zap size={15} strokeWidth={2.5} />
            {busy ? "Encoding…" : "Encode container"}
          </button>
          <button className="btn btn-ghost" onClick={download} disabled={!result}>
            <Download size={14} /> .stg
          </button>
          <button className="btn btn-ghost" onClick={() => copy("hex")} disabled={!result}>
            {copied === "hex" ? <Check size={14} /> : <Copy size={14} />} hex
          </button>
          <button className="btn btn-ghost" onClick={() => copy("json")} disabled={!result}>
            {copied === "json" ? <Check size={14} /> : <Braces size={14} />} JSON
          </button>
          {result ? (
            <span className="ml-auto font-mono2 text-[0.68rem] text-slate-500">
              {result.elapsedMs.toFixed(1)} ms
            </span>
          ) : null}
        </div>
      </section>

      {/* ------------------------------ Result column ----------------------------- */}
      <section className="panel flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-emerald-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">CONTAINER OUTPUT</h2>
          </div>
          {result ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="chip chip-info">
                STG<b>{result.parsed.formatVersion}</b>
              </span>
              {result.parsed.compressed ? <span className="chip chip-violet">zlib</span> : null}
              {result.parsed.encrypted ? (
                <span className="chip chip-warn">
                  <Lock size={10} /> AEAD
                </span>
              ) : null}
              {result.parsed.hmac ? <span className="chip chip-warn">HMAC</span> : null}
              <span className="chip chip-ok">
                <ShieldCheck size={10} />{" "}
                {result.parsed.integrity === "aead"
                  ? "authenticated"
                  : result.parsed.integrity === "hmac"
                    ? "hmac ok"
                    : "sha-256 ok"}
              </span>
            </div>
          ) : null}
        </div>

        {!result ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-700/70 py-14 text-center">
            <svg width="88" height="88" viewBox="0 0 88 88" fill="none" aria-hidden="true">
              <circle cx="44" cy="44" r="40" stroke="rgba(148,163,184,0.25)" strokeWidth="2" strokeDasharray="5 7" />
              <circle cx="44" cy="44" r="22" stroke="rgba(34,211,238,0.45)" strokeWidth="2" />
              <circle cx="44" cy="44" r="6" fill="rgba(52,211,153,0.55)" />
              <path d="M44 4 A40 40 0 0 1 78.6 30" stroke="#22d3ee" strokeWidth="3.5" strokeLinecap="round" />
            </svg>
            <div className="text-sm font-semibold text-slate-300">Nothing encoded yet</div>
            <p className="max-w-xs text-[0.72rem] leading-relaxed text-slate-500">
              Pick a sample, tune the rotation and hit{" "}
              <span className="font-semibold text-cyan-300">Encode container</span> to see the
              byte map come alive.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { label: "Size", value: `${result.bytes.length.toLocaleString()} B` },
                { label: "vs JSON", value: ratio !== null ? `${Math.round(ratio * 100)}%` : "—" },
                { label: "Records", value: String(result.parsed.records.length) },
                { label: "Blocks", value: String(result.parsed.blockCount) },
              ].map((stat) => (
                <div key={stat.label} className="panel-inset px-3 py-2 text-center">
                  <div className="text-[0.58rem] font-bold uppercase tracking-widest text-slate-500">
                    {stat.label}
                  </div>
                  <div className="font-mono2 text-lg font-bold text-slate-100">{stat.value}</div>
                </div>
              ))}
            </div>

            <ByteMap
              segments={result.parsed.segments}
              totalBytes={result.bytes.length}
              selectedKey={selectedSegment?.key ?? null}
              onSelect={(segment) => setSelectedSegment(segment)}
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
              bytes={result.bytes}
              highlight={
                selectedSegment
                  ? { offset: selectedSegment.offset, length: selectedSegment.length }
                  : null
              }
            />

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="field-label !mb-0">Schema ({Object.keys(result.parsed.schemaFields).length} fields)</span>
                <button
                  className="flex items-center gap-1.5 text-[0.65rem] font-semibold text-slate-400 hover:text-slate-200"
                  onClick={() => setLogicalOrder((v) => !v)}
                >
                  <span className="toggle scale-[0.72]" data-on={logicalOrder} aria-hidden="true" />
                  logical read order
                </button>
              </div>
              <div className="mb-2 flex max-h-20 flex-wrap gap-1 overflow-y-auto nice-scroll">
                {Object.entries(result.parsed.schemaFields).map(([field, kind]) => (
                  <span key={field} className="chip !normal-case !tracking-normal">
                    <span className="font-mono2 text-slate-300">{field}</span>
                    <span className="text-cyan-300/90">{kind}</span>
                  </span>
                ))}
              </div>
              <BlockList
                blocks={result.parsed.blocks}
                rotationState={result.parsed.rotationState}
                logicalOrder={logicalOrder}
              />
            </div>
          </>
        )}
      </section>
    </div>
  );
}
