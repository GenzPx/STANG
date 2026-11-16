import { useState } from "react";
import {
  Box,
  Boxes,
  CircleDot,
  FileKey2,
  Fingerprint,
  Layers,
  Lock,
  ShieldCheck,
  Table2,
  Zap,
} from "lucide-react";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "layout", label: "Binary layout" },
  { id: "rotation", label: "Rotation model" },
  { id: "schema", label: "Schema" },
  { id: "integrity", label: "Integrity & encryption" },
  { id: "limits", label: "Limits & errors" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function Byte({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex h-9 w-36 flex-none items-center justify-center rounded-md font-mono2 text-[0.62rem] font-bold uppercase tracking-wider ${tone}`}
      >
        {label}
      </span>
      <code className="font-mono2 text-[0.7rem] text-slate-300">{value}</code>
    </div>
  );
}

export function SpecPanel() {
  const [active, setActive] = useState<SectionId>("overview");

  return (
    <div className="grid gap-5 lg:grid-cols-[220px_1fr]">
      <nav className="panel h-fit p-3 lg:sticky lg:top-20" aria-label="Spec sections">
        <div className="px-2 pb-2 text-[0.62rem] font-bold uppercase tracking-widest text-slate-500">
          STG2 specification
        </div>
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            onClick={() => setActive(section.id)}
            className={`block w-full rounded-lg px-3 py-2 text-left text-[0.8rem] font-medium transition-colors ${
              active === section.id
                ? "bg-cyan-400/15 text-cyan-300"
                : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            }`}
          >
            {section.label}
          </button>
        ))}
        <div className="mt-3 border-t border-slate-800 px-2 pt-3 text-[0.62rem] leading-relaxed text-slate-500">
          The canonical reference lives in{" "}
          <code className="text-slate-300">SPEC.md</code> in the repository. This page is the
          friendly tour.
        </div>
      </nav>

      <div className="panel min-h-[30rem] p-6">
        {active === "overview" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <Boxes size={22} className="text-cyan-300" />
              <h2 className="text-xl font-black text-slate-100">What is STANG?</h2>
            </div>
            <p className="mt-3 text-[0.9rem] leading-relaxed text-slate-300">
              STANG is a self-describing, versioned{" "}
              <em>rotational data container</em>. Records are packed round-robin into a fixed
              set of blocks, the layout is sealed with a trailer digest, and an integer in the
              header encodes the <strong>rotation state</strong> — the logical cursor the
              reader starts from. The physical bytes never move; turning is a view, not a copy.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {[
                { icon: <Zap size={16} />, title: "Deterministic", body: "Canonical JSON with sorted keys. Same input, same bytes — byte-for-byte reproducible across Python and this browser." },
                { icon: <ShieldCheck size={16} />, title: "Sealed", body: "Every container ends with a digest over everything before it. SHA-256, HMAC-SHA256, or an AEAD construction for encrypted files." },
                { icon: <CircleDot size={16} />, title: "Rotational", body: "Access order is defined by rotation state, not file order. Rotating costs one header rewrite, never a data shuffle." },
              ].map((card, index) => (
                <div key={index} className="panel-inset p-4">
                  <div className="text-cyan-300">{card.icon}</div>
                  <div className="mt-1.5 text-[0.8rem] font-bold text-slate-100">{card.title}</div>
                  <p className="mt-1 text-[0.7rem] leading-relaxed text-slate-400">{card.body}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-[0.72rem] text-slate-400">
              <span className="font-bold text-slate-200">Not a database.</span> STANG stores and
              hands back structured data. It does not index, query, join or transact. Think of it
              as a portable, tamper-evident envelope for records — or a building block for
              appliances that move them.
            </div>
          </div>
        ) : null}

        {active === "layout" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <Layers size={22} className="text-violet-300" />
              <h2 className="text-xl font-black text-slate-100">Binary layout — STG2</h2>
            </div>
            <p className="mt-2 text-[0.82rem] text-slate-400">
              All integers are big-endian. Offsets below are decimal. The extension carries the
              schema and (when encrypted) the KDF parameters as canonical JSON.
            </p>
            <div className="mt-4 space-y-2">
              <Byte label="Header · 32 B" value="magic 'STG2' · version u8=2 · flags u8 · rotation u32be · ext_len u32be · block_count u16be · salt 16 B" tone="bg-cyan-900/70 text-cyan-300" />
              <Byte label="Extension · ext_len B" value='canonical JSON: {"schema":{"fields":{…}}} (+ {"kdf":{"name":"pbkdf2-sha256","iterations":100000,"key_len":64}} when encrypted)' tone="bg-violet-900/70 text-violet-300" />
              <Byte label="Block entry" value="blob_len u32be · blob — plaintext is canonical JSON of the block's records; zlib-compressed when flags&0x01; nonce(16 B) ‖ ciphertext when flags&0x02" tone="bg-emerald-900/70 text-emerald-300" />
              <Byte label="Trailer · 32 B" value="SHA-256, or HMAC-SHA256 when keyed/encrypted — over every preceding byte" tone="bg-rose-900/70 text-rose-300" />
            </div>
            <div className="mt-5">
              <span className="field-label">Flags bitfield</span>
              <table className="data-table">
                <thead>
                  <tr><th>Bit</th><th>Name</th><th>Meaning</th></tr>
                </thead>
                <tbody>
                  <tr><td>0x01</td><td>COMPRESSED</td><td>Each block payload is zlib (RFC 1950) compressed</td></tr>
                  <tr><td>0x02</td><td>ENCRYPTED</td><td>Blocks are AEAD-sealed; trailer is HMAC-SHA256 (Encrypt-then-MAC)</td></tr>
                  <tr><td>0x04</td><td>HMAC</td><td>Truncated-free HMAC-SHA256 authenticity without confidentiality</td></tr>
                </tbody>
              </table>
            </div>
            <div className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/5 p-3 text-[0.7rem] text-amber-200/90">
              <span className="font-bold">STG1 (legacy)</span> — 14-byte header, absolute-offset
              block table between schema and blocks, SHA-256 trailer. Still readable and writable
              everywhere, but frozen: no compression, no crypto. Convert with{" "}
              <code className="font-mono2">stang convert in.stg out.stg --to stg2</code>.
            </div>
          </div>
        ) : null}

        {active === "rotation" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <CircleDot size={22} className="text-emerald-300" />
              <h2 className="text-xl font-black text-slate-100">The rotation model</h2>
            </div>
            <p className="mt-2 text-[0.82rem] leading-relaxed text-slate-400">
              Records are distributed round-robin: record <em>i</em> lands in block{" "}
              <code className="font-mono2 text-cyan-300">i mod block_count</code>. Reading starts
              at <code className="font-mono2 text-cyan-300">header.rotation_state</code> and wraps
              around. Rotation state is an integer in the header — <strong>rotating a container
              rewrites 4 bytes</strong>, never the payload.
            </p>
            <pre className="terminal mt-4 overflow-x-auto nice-scroll p-4 text-slate-300">
{`records  →  block 0: R0 R4 R8 …     rotation_state = 1
             block 1: R1 R5 R9 …     read order:   block 1 → 2 → 3 → 0
             block 2: R2 R6 R10 …
             block 3: R3 R7 R11 …`}
            </pre>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="panel-inset p-4">
                <div className="text-[0.72rem] font-bold text-slate-100">Decode semantics</div>
                <p className="mt-1 text-[0.7rem] leading-relaxed text-slate-400">
                  Decoding always materializes records in <em>canonical</em> (storage) order, so{" "}
                  <code className="font-mono2">decode(encode(x)) == x</code> regardless of rotation.
                  The rotation is a logical access hint, preserved through round-trips.
                </p>
              </div>
              <div className="panel-inset p-4">
                <div className="text-[0.72rem] font-bold text-slate-100">Rotate in place</div>
                <p className="mt-1 text-[0.7rem] leading-relaxed text-slate-400">
                  <code className="font-mono2">stang rotate data.stg +2</code> decrypts, bumps the
                  counter modulo block_count, and re-seals. On encrypted files it needs the
                  passphrase; the bytes are re-encrypted with fresh nonces.
                </p>
              </div>
            </div>
          </div>
        ) : null}

        {active === "schema" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <Table2 size={22} className="text-amber-300" />
              <h2 className="text-xl font-black text-slate-100">Self-describing schema</h2>
            </div>
            <p className="mt-2 text-[0.82rem] leading-relaxed text-slate-400">
              The extension stores a dot-flattened type map: nested objects collapse into dotted
              paths, arrays and objects stay opaque kinds. Types:{" "}
              <code className="font-mono2">string · integer · float · boolean · null · array · object · any</code>.
              Numeric widening promotes integer+float → float; conflicting kinds collapse to any.
            </p>
            <pre className="terminal mt-4 overflow-x-auto nice-scroll p-4 text-slate-300">
{`{
  "id": "integer",
  "meta.city": "string",
  "meta.score": "float",
  "tags": "array",
  "active": "boolean"
}`}
            </pre>
            <p className="mt-3 text-[0.7rem] text-slate-500">
              Schema inference merges every record (not just the first), so heterogeneous inputs
              still get a truthful map. When encrypted, field names stay visible in the clear —
              only the block payloads are sealed. Adopt opaque field names if that matters.
            </p>
          </div>
        ) : null}

        {active === "integrity" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <Lock size={22} className="text-rose-300" />
              <h2 className="text-xl font-black text-slate-100">Integrity &amp; encryption</h2>
            </div>
            <p className="mt-2 text-[0.82rem] text-slate-400">
              STG2 picks its trailer by flags. AEAD encrypts each block independently, then
              authenticates the whole payload — Encrypt-then-MAC, single pass.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {[
                { icon: <Fingerprint size={16} />, title: "SHA-256", tag: "flags = 0x00", body: "Plain digest. Anyone can read, anyone can tamper-check. Default for public data.", tone: "text-slate-300" },
                { icon: <ShieldCheck size={16} />, title: "HMAC-SHA256", tag: "flags = 0x04", body: "Keyed authenticity without secrecy. Readers need the key only to verify; tampering is detectable by anyone holding it.", tone: "text-amber-300" },
                { icon: <FileKey2 size={16} />, title: "AEAD (PBKDF2+HMAC)", tag: "flags = 0x02", body: "PBKDF2-HMAC-SHA256 (100k iters) → enc master + MAC key. HMAC-SHA256 counter-mode stream, per-block nonce, Encrypt-then-MAC trailer.", tone: "text-violet-300" },
              ].map((mode, index) => (
                <div key={index} className="panel-inset p-4">
                  <div className={mode.tone}>{mode.icon}</div>
                  <div className="mt-1.5 text-[0.85rem] font-bold text-slate-100">{mode.title}</div>
                  <code className="font-mono2 text-[0.62rem] text-slate-500">{mode.tag}</code>
                  <p className="mt-1.5 text-[0.7rem] leading-relaxed text-slate-400">{mode.body}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <span className="text-[0.7rem] font-bold uppercase tracking-widest text-slate-500">
                Key schedule (AEAD)
              </span>
              <pre className="terminal mt-2 overflow-x-auto nice-scroll !border-0 !bg-transparent !p-0 text-[0.68rem] text-slate-300">
{`salt     = random 16 B (stored in header)
keys     = PBKDF2-HMAC-SHA256(passphrase, salt, 100_000, 64 B)
         = enc_master(32 B) ‖ mac_key(32 B)
blockkey = HMAC-SHA256(enc_master, "stang-blk" ‖ u32be(i) ‖ nonce_i)
stream   = HMAC-SHA256(blockkey, u64be(counter))  xor  plaintext
trailer  = HMAC-SHA256(mac_key, header ‖ ext ‖ blocks)`}
              </pre>
            </div>
          </div>
        ) : null}

        {active === "limits" ? (
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <Box size={22} className="text-slate-300" />
              <h2 className="text-xl font-black text-slate-100">Limits &amp; error contract</h2>
            </div>
            <table className="data-table mt-4">
              <thead>
                <tr><th>Item</th><th>Limit / behaviour</th></tr>
              </thead>
              <tbody>
                <tr><td>Blocks per container</td><td>65 535 (u16be); 4 by default, 1–16 in the studio</td></tr>
                <tr><td>Header extension</td><td>4 MiB hard cap</td></tr>
                <tr><td>Block blob</td><td>4 GiB - 1 (u32be length)</td></tr>
                <tr><td>rotation_state</td><td>u32be, normalized modulo block_count</td></tr>
                <tr><td>Trailer mismatch</td><td>ContainerError / AuthenticationError — nothing is returned</td></tr>
                <tr><td>Unknown magic</td><td>Rejected before any parsing</td></tr>
                <tr><td>Unsupported version</td><td>Rejected with the offending version in the message</td></tr>
                <tr><td>Truncated file</td><td>Rejected; bounds are checked at every region</td></tr>
              </tbody>
            </table>
            <p className="mt-4 text-[0.7rem] leading-relaxed text-slate-500">
              Every failure mode raises before a single record is returned to the caller — a
              tampered or corrupt STANG file never yields partial data. Both the Python package
              and this studio enforce the same contract.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
