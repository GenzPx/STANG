/**
 * STANG wire-format codec (STG1 + STG2) for the browser and Node.
 *
 * Byte-compatible with the Python `stang` package. Cross-implementation
 * conformance is verified by `scripts/conformance.mjs` against
 * `tests/fixtures/golden*.stg`.
 *
 * Formats
 *   STG1 (legacy): 14-byte header, embedded absolute-offset block table,
 *                  32-byte SHA-256 trailer.
 *   STG2 (current): 32-byte header, JSON header extension (schema + KDF),
 *                   length-prefixed block entries, optional zlib compression
 *                   and PBKDF2/HMAC-SHA256 authenticated encryption,
 *                   Encrypt-then-MAC trailer.
 */

export const MAGIC_V1 = "STG1";
export const MAGIC_V2 = "STG2";
export const FLAG_COMPRESSED = 0x01;
export const FLAG_ENCRYPTED = 0x02;
export const FLAG_HMAC = 0x04;
export const NONCE_SIZE = 16;
export const V2_HEADER_SIZE = 32;
export const V1_HEADER_SIZE = 14;
export const PBKDF2_ITERATIONS = 100_000;
const BLOCK_DOMAIN_PREFIX = new TextEncoder().encode("stang-blk");

export type StgFormat = "stg1" | "stg2";

export interface StgSegment {
  key: string;
  label: string;
  detail: string;
  offset: number;
  length: number;
  kind: "header" | "ext" | "table" | "nonce" | "block" | "trailer";
  blockIndex?: number;
}

export interface HeaderSummary {
  magic: string;
  version: number;
  flags: number;
  compressed: boolean;
  encrypted: boolean;
  hmac: boolean;
  rotationState: number;
  blockCount: number;
  sizeBytes: number;
  /** Human readable flag list, e.g. ["compressed", "encrypted"]. */
  flagNames: string[];
}

export interface ParsedContainer {
  formatVersion: number;
  flags: number;
  compressed: boolean;
  encrypted: boolean;
  hmac: boolean;
  rotationState: number;
  blockCount: number;
  schemaFields: Record<string, string>;
  blocks: Record<string, unknown>[][];
  records: Record<string, unknown>[];
  segments: StgSegment[];
  totalBytes: number;
  integrity: "sha256" | "hmac" | "aead";
}

export class StgError extends Error {}

/* ------------------------------------------------------------------ */
/* Byte helpers                                                        */
/* ------------------------------------------------------------------ */

export function concatBytes(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

export function utf8(text: string): Uint8Array {
  return textEncoder.encode(text);
}

export function fromUtf8(bytes: Uint8Array): string {
  return textDecoder.decode(bytes);
}

export function hexDump(bytes: Uint8Array, maxRows = 512): string {
  const lines: string[] = [];
  const rows = Math.min(Math.ceil(bytes.length / 16), maxRows);
  for (let row = 0; row < rows; row++) {
    const offset = row * 16;
    const slice = bytes.subarray(offset, Math.min(offset + 16, bytes.length));
    const hex = Array.from(slice, (b) => b.toString(16).padStart(2, "0")).join(" ");
    const hexPadded = hex.padEnd(47, " ");
    let ascii = "";
    for (const b of slice) ascii += b >= 32 && b < 127 ? String.fromCharCode(b) : ".";
    lines.push(`${offset.toString(16).padStart(8, "0")}  ${hexPadded}  |${ascii}|`);
  }
  if (rows < Math.ceil(bytes.length / 16)) {
    lines.push(`… (${bytes.length - rows * 16} more bytes)`);
  }
  return lines.join("\n");
}

export function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function fromHex(hex: string): Uint8Array {
  const clean = hex.replace(/0x/gi, "").replace(/[\s,;:-]/g, "");
  if (clean.length % 2 !== 0 || /[^0-9a-f]/i.test(clean)) {
    throw new StgError("Hex payload contains invalid characters.");
  }
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

/* ------------------------------------------------------------------ */
/* Canonical JSON (Python `json.dumps(..., sort_keys=True)` compatible) */
/* ------------------------------------------------------------------ */

function numberToCanonical(value: number): string {
  if (!Number.isFinite(value)) {
    throw new StgError("Non-finite numbers cannot be encoded in JSON.");
  }
  if (Number.isInteger(value) && Math.abs(value) < 1e16) {
    return String(value);
  }
  let text = String(value);
  // Python renders exponents as e-07 / e+21; V8 renders e-7 / e+21.
  text = text.replace(/e-(\d)$/, "e-0$1");
  return text;
}

function writeCanonical(value: unknown): string {
  if (value === null || value === undefined) return "null";
  const kind = typeof value;
  if (kind === "boolean") return value ? "true" : "false";
  if (kind === "number") return numberToCanonical(value as number);
  if (kind === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return `[${value.map(writeCanonical).join(",")}]`;
  }
  if (kind === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record).sort();
    const fields = keys.map((key) => `${JSON.stringify(key)}:${writeCanonical(record[key])}`);
    return `{${fields.join(",")}}`;
  }
  throw new StgError(`Unsupported JSON value type: ${kind}`);
}

export function canonicalJsonString(value: unknown): string {
  return writeCanonical(value);
}

export function canonicalJsonBytes(value: unknown): Uint8Array {
  return utf8(writeCanonical(value));
}

/* ------------------------------------------------------------------ */
/* Crypto primitives (Web Crypto, PBKDF2 + HMAC-SHA256)                */
/* ------------------------------------------------------------------ */

async function sha256(data: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", data as BufferSource));
}

async function hmacSha256(key: Uint8Array, data: Uint8Array): Promise<Uint8Array> {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    key as BufferSource,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", cryptoKey, data as BufferSource));
}

async function pbkdf2Sha256(
  passphrase: Uint8Array,
  salt: Uint8Array,
  iterations: number,
  bits: number,
): Promise<Uint8Array> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    passphrase as BufferSource,
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  return new Uint8Array(
    await crypto.subtle.deriveBits(
      { name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations },
      baseKey,
      bits,
    ),
  );
}

async function deriveKeys(
  passphrase: string | Uint8Array,
  salt: Uint8Array,
  iterations = PBKDF2_ITERATIONS,
): Promise<{ encMaster: Uint8Array; macKey: Uint8Array }> {
  if (salt.length !== NONCE_SIZE) {
    throw new StgError(`Salt must be ${NONCE_SIZE} bytes.`);
  }
  const raw = typeof passphrase === "string" ? utf8(passphrase) : passphrase;
  if (raw.length === 0) {
    throw new StgError("Encryption passphrase must not be empty.");
  }
  const derived = await pbkdf2Sha256(raw, salt, iterations, 512);
  return { encMaster: derived.slice(0, 32), macKey: derived.slice(32, 64) };
}

function xorKeystream(keystreamParts: Uint8Array[], data: Uint8Array): Uint8Array {
  const out = new Uint8Array(data.length);
  let offset = 0;
  for (const ks of keystreamParts) {
    for (let i = 0; i < ks.length && offset + i < data.length; i++) {
      out[offset + i] = data[offset + i] ^ ks[i];
    }
    offset += ks.length;
    if (offset >= data.length) break;
  }
  return out;
}

async function blockKeyStreamParts(
  encMaster: Uint8Array,
  blockIndex: number,
  nonce: Uint8Array,
  length: number,
): Promise<Uint8Array[]> {
  const info = new Uint8Array(BLOCK_DOMAIN_PREFIX.length + 4 + NONCE_SIZE);
  info.set(BLOCK_DOMAIN_PREFIX, 0);
  new DataView(info.buffer).setUint32(BLOCK_DOMAIN_PREFIX.length, blockIndex, false);
  info.set(nonce, BLOCK_DOMAIN_PREFIX.length + 4);
  const blockKey = await hmacSha256(encMaster, info);

  const counter = new Uint8Array(8);
  const counterView = new DataView(counter.buffer);
  const parts: Uint8Array[] = [];
  let remaining = length;
  let count = 0;
  while (remaining > 0) {
    counterView.setBigUint64(0, BigInt(count), false);
    parts.push(await hmacSha256(blockKey, counter));
    remaining -= 32;
    count += 1;
  }
  return parts;
}

export async function encryptBlock(
  plaintext: Uint8Array,
  encMaster: Uint8Array,
  blockIndex: number,
  nonce?: Uint8Array,
): Promise<Uint8Array> {
  const actualNonce = nonce ?? crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
  if (actualNonce.length !== NONCE_SIZE) {
    throw new StgError(`Block nonce must be ${NONCE_SIZE} bytes.`);
  }
  const parts = await blockKeyStreamParts(encMaster, blockIndex, actualNonce, plaintext.length);
  return concatBytes([actualNonce, xorKeystream(parts, plaintext)]);
}

export async function decryptBlock(
  blob: Uint8Array,
  encMaster: Uint8Array,
  blockIndex: number,
): Promise<Uint8Array> {
  if (blob.length < NONCE_SIZE) {
    throw new StgError("Encrypted block is shorter than the nonce length.");
  }
  const nonce = blob.slice(0, NONCE_SIZE);
  const ciphertext = blob.slice(NONCE_SIZE);
  const parts = await blockKeyStreamParts(encMaster, blockIndex, nonce, ciphertext.length);
  return xorKeystream(parts, ciphertext);
}

async function zlibCompress(data: Uint8Array): Promise<Uint8Array> {
  const stream = new CompressionStream("deflate");
  const writer = stream.writable.getWriter();
  void writer.write(data as BufferSource);
  void writer.close();
  return new Uint8Array(await new Response(stream.readable).arrayBuffer());
}

async function zlibDecompress(data: Uint8Array): Promise<Uint8Array> {
  const stream = new DecompressionStream("deflate");
  const writer = stream.writable.getWriter();
  void writer.write(data as BufferSource);
  void writer.close();
  return new Uint8Array(await new Response(stream.readable).arrayBuffer());
}

/* ------------------------------------------------------------------ */
/* Record partitioning (round-robin, interleaved merge)                */
/* ------------------------------------------------------------------ */

export function partitionRecords(
  records: Record<string, unknown>[],
  blockCount: number,
): Record<string, unknown>[][] {
  if (blockCount <= 0) throw new StgError("block_count must be positive");
  const blocks: Record<string, unknown>[][] = Array.from({ length: blockCount }, () => []);
  records.forEach((record, index) => {
    blocks[index % blockCount].push(record);
  });
  return blocks;
}

export function mergeBlocks(blocks: Record<string, unknown>[][]): Record<string, unknown>[] {
  if (blocks.length === 0) return [];
  const result: Record<string, unknown>[] = [];
  const maxLen = Math.max(...blocks.map((block) => block.length));
  for (let offset = 0; offset < maxLen; offset++) {
    for (const block of blocks) {
      if (offset < block.length) result.push(block[offset]);
    }
  }
  return result;
}

export interface SchemaInfo {
  fields: Record<string, string>;
}

export function classifyValue(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return Number.isInteger(value) ? "integer" : "float";
  if (typeof value === "string") return "string";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object") return "object";
  return "any";
}

function mergeFieldTypes(existing: string, incoming: string): string {
  if (existing === incoming) return existing;
  if (existing === "null") return incoming;
  if (incoming === "null") return existing;
  if (
    (existing === "integer" && incoming === "float") ||
    (existing === "float" && incoming === "integer")
  ) {
    return "float";
  }
  return "any";
}

export function inferSchemaFields(records: Record<string, unknown>[]): Record<string, string> {
  const fields: Record<string, string> = {};
  const mergeRecord = (prefix: string, value: unknown) => {
    const kind = classifyValue(value);
    if (kind === "object" && value && !Array.isArray(value)) {
      const entries = Object.entries(value as Record<string, unknown>);
      if (entries.length === 0) {
        setField(fields, prefix, "object");
        return;
      }
      for (const [subKey, subValue] of entries) {
        mergeRecord(`${prefix}.${subKey}`, subValue);
      }
      return;
    }
    setField(fields, prefix, kind);
  };
  const setField = (target: Record<string, string>, key: string, kind: string) => {
    if (key in target) {
      target[key] = mergeFieldTypes(target[key], kind);
    } else {
      target[key] = kind;
    }
  };
  for (const record of records) {
    for (const [key, value] of Object.entries(record)) {
      mergeRecord(key, value);
    }
  }
  return fields;
}

/* ------------------------------------------------------------------ */
/* Serialization                                                       */
/* ------------------------------------------------------------------ */

export interface SerializeOptions {
  records: Record<string, unknown>[];
  blockCount?: number;
  rotationState?: number;
  format?: StgFormat;
  compress?: boolean;
  passphrase?: string;
  integrityKey?: string;
  salt?: Uint8Array;
  nonces?: Uint8Array[];
}

function u32be(value: number): Uint8Array {
  const out = new Uint8Array(4);
  new DataView(out.buffer).setUint32(0, value >>> 0, false);
  return out;
}

function u16be(value: number): Uint8Array {
  const out = new Uint8Array(2);
  new DataView(out.buffer).setUint16(0, value, false);
  return out;
}

export async function serializeStg(options: SerializeOptions): Promise<Uint8Array> {
  const format = options.format ?? "stg2";
  if (format === "stg1") {
    if (options.compress || options.passphrase || options.integrityKey) {
      throw new StgError(
        "STG1 cannot represent compression, encryption or HMAC. Use stg2.",
      );
    }
    return serializeStgV1(options);
  }
  return serializeStgV2(options);
}

async function serializeStgV1(options: SerializeOptions): Promise<Uint8Array> {
  const blockCount = options.blockCount ?? 4;
  const rotationState = (options.rotationState ?? 0) % blockCount;
  const records = options.records;
  const schemaFields = inferSchemaFields(records);
  const schemaBytes = canonicalJsonBytes({ fields: schemaFields });
  const blocks = partitionRecords(records, blockCount);
  const blockBytes = blocks.map((block) => canonicalJsonBytes(block));

  const headerSize = V1_HEADER_SIZE;
  const baseOffset = headerSize + schemaBytes.length;

  // Iterate: table length depends on offsets, offsets depend on table length.
  let tableBytes = canonicalJsonBytes(blockBytes.map((b) => [0, b.length]));
  for (;;) {
    let offset = baseOffset + tableBytes.length;
    const table = blockBytes.map((b) => {
      const entry = [offset, b.length];
      offset += b.length;
      return entry;
    });
    const next = canonicalJsonBytes(table);
    if (next.length === tableBytes.length) {
      tableBytes = next;
      break;
    }
    tableBytes = next;
  }

  const header = concatBytes([
    utf8(MAGIC_V1),
    new Uint8Array([1, 0]),
    u32be(rotationState),
    u32be(schemaBytes.length),
  ]);
  const payload = concatBytes([header, schemaBytes, tableBytes, ...blockBytes]);
  const digest = await sha256(payload);
  return concatBytes([payload, digest]);
}

async function serializeStgV2(options: SerializeOptions): Promise<Uint8Array> {
  const blockCount = options.blockCount ?? 4;
  if (blockCount <= 0) throw new StgError("block_count must be positive");
  const rotationState = ((options.rotationState ?? 0) % blockCount + blockCount) % blockCount;
  const compress = options.compress ?? false;
  const passphrase = options.passphrase;
  const integrityKey = options.integrityKey;
  if (passphrase && integrityKey) {
    throw new StgError("Pass either passphrase (encryption) or integrityKey (HMAC), not both.");
  }
  let flags = 0;
  if (compress) flags |= FLAG_COMPRESSED;
  if (passphrase) flags |= FLAG_ENCRYPTED;
  else if (integrityKey) flags |= FLAG_HMAC;

  const records = options.records;
  const schemaFields = inferSchemaFields(records);
  const extension: Record<string, unknown> = { schema: { fields: schemaFields } };
  if (passphrase) {
    extension.kdf = { name: "pbkdf2-sha256", iterations: PBKDF2_ITERATIONS, key_len: 64 };
  }
  const extBytes = canonicalJsonBytes(extension);

  // Plain containers carry a zero salt (matching the Python implementation);
  // encrypted containers get a fresh random salt per serialization.
  const salt =
    options.salt ??
    (passphrase ? crypto.getRandomValues(new Uint8Array(NONCE_SIZE)) : new Uint8Array(NONCE_SIZE));
  if (salt.length !== NONCE_SIZE) throw new StgError(`Salt must be ${NONCE_SIZE} bytes.`);

  let encMaster: Uint8Array | null = null;
  let macKey: Uint8Array | null = null;
  if (passphrase) {
    ({ encMaster, macKey } = await deriveKeys(passphrase, salt));
  }

  const blocks = partitionRecords(records, blockCount);
  const parts: Uint8Array[] = [];
  const header = concatBytes([
    utf8(MAGIC_V2),
    new Uint8Array([2, flags]),
    u32be(rotationState),
    u32be(extBytes.length),
    u16be(blockCount),
    salt,
  ]);
  parts.push(header, extBytes);

  for (let index = 0; index < blocks.length; index++) {
    let plaintext = canonicalJsonBytes(blocks[index]);
    if (compress) {
      plaintext = await zlibCompress(plaintext);
    }
    let blob: Uint8Array;
    if (encMaster) {
      const nonce = options.nonces?.[index];
      blob = await encryptBlock(plaintext, encMaster, index, nonce);
    } else {
      blob = plaintext;
    }
    parts.push(u32be(blob.length), blob);
  }

  const payload = concatBytes(parts);
  let trailer: Uint8Array;
  if (passphrase && macKey) {
    trailer = await hmacSha256(macKey, payload);
  } else if (integrityKey) {
    trailer = await hmacSha256(utf8(integrityKey), payload);
  } else {
    trailer = await sha256(payload);
  }
  return concatBytes([payload, trailer]);
}

/* ------------------------------------------------------------------ */
/* Parsing                                                             */
/* ------------------------------------------------------------------ */

export interface ParseOptions {
  passphrase?: string;
  integrityKey?: string;
}

export function sniffHeader(data: Uint8Array): HeaderSummary | null {
  if (data.length < V1_HEADER_SIZE + 32) return null;
  const magic = fromUtf8(data.slice(0, 4));
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  if (magic === MAGIC_V1) {
    const version = view.getUint8(4);
    const flags = view.getUint8(5);
    return {
      magic,
      version,
      flags,
      compressed: false,
      encrypted: false,
      hmac: false,
      rotationState: view.getUint32(6, false),
      blockCount: 0,
      sizeBytes: data.length,
      flagNames: [],
    };
  }
  if (magic === MAGIC_V2) {
    const version = view.getUint8(4);
    const flags = view.getUint8(5);
    const flagNames: string[] = [];
    if (flags & FLAG_COMPRESSED) flagNames.push("compressed");
    if (flags & FLAG_ENCRYPTED) flagNames.push("encrypted");
    if (flags & FLAG_HMAC) flagNames.push("hmac");
    return {
      magic,
      version,
      flags,
      compressed: Boolean(flags & FLAG_COMPRESSED),
      encrypted: Boolean(flags & FLAG_ENCRYPTED),
      hmac: Boolean(flags & FLAG_HMAC),
      rotationState: view.getUint32(6, false),
      blockCount: view.getUint16(14, false),
      sizeBytes: data.length,
      flagNames,
    };
  }
  return null;
}

function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

/**
 * Scan bytes for the end of the first JSON value starting at `start`.
 * Byte offsets are used because the STG1 table is pure ASCII, so byte and
 * character positions coincide. Mirrors Python's `json.JSONDecoder().raw_decode`.
 */
function scanJsonValueEnd(data: Uint8Array, start: number): number {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < data.length; i++) {
    const byte = data[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (byte === 0x5c /* \ */) {
        escaped = true;
      } else if (byte === 0x22 /* " */) {
        inString = false;
      }
      continue;
    }
    if (byte === 0x22) {
      inString = true;
      continue;
    }
    if (byte === 0x5b /* [ */ || byte === 0x7b /* { */) depth++;
    else if (byte === 0x5d /* ] */ || byte === 0x7d /* } */) {
      depth--;
      if (depth === 0) return i + 1;
    }
  }
  throw new StgError("Failed to locate the end of the JSON value.");
}

export async function parseStg(
  data: Uint8Array,
  options: ParseOptions = {},
): Promise<ParsedContainer> {
  if (data.length < V1_HEADER_SIZE + 32) {
    throw new StgError("File too short to be a valid STG container.");
  }
  const magic = fromUtf8(data.slice(0, 4));
  if (magic === MAGIC_V1) return parseStgV1(data);
  if (magic === MAGIC_V2) return parseStgV2(data, options);
  throw new StgError(`Invalid magic bytes: expected STG1 or STG2, got "${magic}"`);
}

async function parseStgV1(data: Uint8Array): Promise<ParsedContainer> {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const version = view.getUint8(4);
  if (version !== 1) throw new StgError(`Unsupported STG version: ${version}`);
  const flags = view.getUint8(5);
  const rotationState = view.getUint32(6, false);
  const schemaLen = view.getUint32(10, false);

  const checksumOffset = data.length - 32;
  const payload = data.slice(0, checksumOffset);
  const expected = data.slice(checksumOffset);
  const actual = await sha256(payload);
  if (!equalBytes(actual, expected)) {
    throw new StgError("Checksum mismatch: container may be corrupted.");
  }

  const schemaBytes = payload.slice(V1_HEADER_SIZE, V1_HEADER_SIZE + schemaLen);
  let schemaFields: Record<string, string>;
  try {
    const parsed = JSON.parse(fromUtf8(schemaBytes)) as { fields?: Record<string, string> };
    schemaFields = parsed.fields ?? {};
  } catch {
    throw new StgError("Failed to parse schema.");
  }

  const tableStart = V1_HEADER_SIZE + schemaLen;
  const tableEnd = scanJsonValueEnd(payload, tableStart);
  let table: [number, number][];
  try {
    table = JSON.parse(fromUtf8(payload.slice(tableStart, tableEnd))) as [number, number][];
    if (!Array.isArray(table)) throw new Error("table not an array");
  } catch {
    throw new StgError("Failed to parse block table.");
  }

  const blocks: Record<string, unknown>[][] = [];
  for (const [offset, size] of table) {
    if (offset + size > payload.length) {
      throw new StgError("Block table points outside payload bounds.");
    }
    const block = JSON.parse(fromUtf8(payload.slice(offset, offset + size))) as Record<
      string,
      unknown
    >[];
    blocks.push(block);
  }

  const segments: StgSegment[] = [
    {
      key: "header",
      label: "Header",
      detail: `magic STG1 · version 1 · flags 0x${flags.toString(16).padStart(2, "0")}`,
      offset: 0,
      length: V1_HEADER_SIZE,
      kind: "header",
    },
    {
      key: "schema",
      label: "Schema",
      detail: "JSON schema (dot-flattened field types)",
      offset: V1_HEADER_SIZE,
      length: schemaLen,
      kind: "ext",
    },
    {
      key: "table",
      label: "Block table",
      detail: "JSON [[offset, size], …] with absolute payload offsets",
      offset: tableStart,
      length: tableEnd - tableStart,
      kind: "table",
    },
  ];
  blocks.forEach((block, index) => {
    const [offset, size] = table[index];
    segments.push({
      key: `block-${index}`,
      label: `Block ${index}`,
      detail: `${block.length} record(s) · ${size} bytes`,
      offset,
      length: size,
      kind: "block",
      blockIndex: index,
    });
  });
  segments.push({
    key: "trailer",
    label: "Trailer",
    detail: "SHA-256 of everything above",
    offset: checksumOffset,
    length: 32,
    kind: "trailer",
  });

  return {
    formatVersion: 1,
    flags,
    compressed: false,
    encrypted: false,
    hmac: false,
    rotationState,
    blockCount: blocks.length,
    schemaFields,
    blocks,
    records: mergeBlocks(blocks),
    segments,
    totalBytes: data.length,
    integrity: "sha256",
  };
}

async function parseStgV2(data: Uint8Array, options: ParseOptions): Promise<ParsedContainer> {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const version = view.getUint8(4);
  if (version !== 2) throw new StgError(`Unsupported STG version: ${version}`);
  const flags = view.getUint8(5);
  const rotationState = view.getUint32(6, false);
  const extLen = view.getUint32(10, false);
  const blockCount = view.getUint16(14, false);
  const salt = data.slice(16, 32);

  if (extLen > 4 * 1024 * 1024) {
    throw new StgError("Header extension exceeds the 4 MiB limit.");
  }
  if ((flags & FLAG_ENCRYPTED) && (flags & FLAG_HMAC)) {
    throw new StgError("Invalid flags: encryption already authenticates the payload.");
  }

  const checksumOffset = data.length - 32;
  if (checksumOffset < V2_HEADER_SIZE) {
    throw new StgError("File too short to be a valid STG2 container.");
  }
  const payload = data.slice(0, checksumOffset);
  const expected = data.slice(checksumOffset);

  const kdfIterations = PBKDF2_ITERATIONS;
  let encMaster: Uint8Array | null = null;
  let macKey: Uint8Array | null = null;
  if (flags & FLAG_ENCRYPTED) {
    if (!options.passphrase) {
      throw new StgError("Container is encrypted. Supply a passphrase to read it.");
    }
    ({ encMaster, macKey } = await deriveKeys(options.passphrase, salt, kdfIterations));
  }

  if (flags & FLAG_ENCRYPTED && macKey) {
    const actual = await hmacSha256(macKey, payload);
    if (!equalBytes(actual, expected)) {
      throw new StgError("Authentication failed: wrong passphrase or corrupted data.");
    }
  } else if (flags & FLAG_HMAC) {
    if (!options.integrityKey) {
      throw new StgError("Container requires an integrity key to be verified.");
    }
    const actual = await hmacSha256(utf8(options.integrityKey), payload);
    if (!equalBytes(actual, expected)) {
      throw new StgError("Integrity check failed: bad key or corrupted data.");
    }
  } else {
    const actual = await sha256(payload);
    if (!equalBytes(actual, expected)) {
      throw new StgError("Checksum mismatch: container may be corrupted.");
    }
  }

  const extStart = V2_HEADER_SIZE;
  const extEnd = extStart + extLen;
  if (extEnd > payload.length) {
    throw new StgError("Header extension points outside the payload.");
  }
  let schemaFields: Record<string, string> = {};
  try {
    const extension = JSON.parse(fromUtf8(payload.slice(extStart, extEnd))) as {
      schema?: { fields?: Record<string, string> };
    };
    schemaFields = extension.schema?.fields ?? {};
  } catch {
    throw new StgError("Failed to parse header extension.");
  }

  const blocks: Record<string, unknown>[][] = [];
  const segments: StgSegment[] = [
    {
      key: "header",
      label: "Header",
      detail: `magic STG2 · version 2 · flags 0x${flags
        .toString(16)
        .padStart(2, "0")}${flags & FLAG_COMPRESSED ? " (zlib)" : ""}`,
      offset: 0,
      length: V2_HEADER_SIZE,
      kind: "header",
    },
    {
      key: "ext",
      label: "Header extension",
      detail: "JSON: schema fields" + ((flags & FLAG_ENCRYPTED) ? " + KDF parameters" : ""),
      offset: extStart,
      length: extLen,
      kind: "ext",
    },
  ];

  let offset = extEnd;
  for (let index = 0; index < blockCount; index++) {
    if (offset + 4 > payload.length) {
      throw new StgError("Unexpected end of container while reading a block length.");
    }
    const blobLen = view.getUint32(offset, false);
    const blobStart = offset + 4;
    if (blobLen > payload.length - blobStart) {
      throw new StgError("Block length points outside the payload.");
    }
    let blob: Uint8Array = payload.slice(blobStart, blobStart + blobLen);

    if (encMaster) {
      segments.push({
        key: `block-${index}-nonce`,
        label: `Block ${index} nonce`,
        detail: "16-byte random nonce (PBKDF2-derived block key)",
        offset: blobStart,
        length: NONCE_SIZE,
        kind: "nonce",
        blockIndex: index,
      });
      segments.push({
        key: `block-${index}-ciphertext`,
        label: `Block ${index} ciphertext`,
        detail: `${blobLen - NONCE_SIZE} bytes, HMAC-SHA256 counter mode`,
        offset: blobStart + NONCE_SIZE,
        length: blobLen - NONCE_SIZE,
        kind: "block",
        blockIndex: index,
      });
      try {
        blob = await decryptBlock(blob, encMaster, index);
      } catch (error) {
        throw new StgError(
          `Failed to decrypt block ${index}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    } else {
      segments.push({
        key: `block-${index}`,
        label: `Block ${index}`,
        detail: `${blobLen} bytes`,
        offset: blobStart,
        length: blobLen,
        kind: "block",
        blockIndex: index,
      });
    }

    if (flags & FLAG_COMPRESSED) {
      try {
        blob = await zlibDecompress(blob);
      } catch {
        throw new StgError(`Failed to decompress block ${index}.`);
      }
    }
    let block: Record<string, unknown>[];
    try {
      block = JSON.parse(fromUtf8(blob)) as Record<string, unknown>[];
    } catch {
      throw new StgError(`Failed to parse data block ${index}.`);
    }
    if (!Array.isArray(block)) {
      throw new StgError(`Data block ${index} must decode to a JSON array.`);
    }
    blocks.push(block);
    offset = blobStart + blobLen;
  }

  if (offset !== payload.length) {
    throw new StgError("Trailing bytes after the last block (container is malformed).");
  }

  segments.push({
    key: "trailer",
    label: "Trailer",
    detail:
      flags & FLAG_ENCRYPTED
        ? "HMAC-SHA256 (Encrypt-then-MAC) over everything above"
        : flags & FLAG_HMAC
          ? "HMAC-SHA256 over everything above"
          : "SHA-256 over everything above",
    offset: checksumOffset,
    length: 32,
    kind: "trailer",
  });

  return {
    formatVersion: 2,
    flags,
    compressed: Boolean(flags & FLAG_COMPRESSED),
    encrypted: Boolean(flags & FLAG_ENCRYPTED),
    hmac: Boolean(flags & FLAG_HMAC),
    rotationState,
    blockCount,
    schemaFields,
    blocks,
    records: mergeBlocks(blocks),
    segments,
    totalBytes: data.length,
    integrity: flags & FLAG_ENCRYPTED ? "aead" : flags & FLAG_HMAC ? "hmac" : "sha256",
  };
}
