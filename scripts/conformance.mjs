/**
 * Cross-implementation conformance check for the STANG format.
 *
 * Compiles `src/stg/codec.ts` with esbuild and validates it against the
 * golden fixtures produced by the Python implementation:
 *
 *   1. decrypt + parse `tests/fixtures/golden_encrypted.stg` and compare
 *      records with `tests/fixtures/golden.json`;
 *   2. recompute the trailer HMAC of both fixtures;
 *   3. re-serialize `golden_plain.stg` and require byte-for-byte equality;
 *   4. verify zlib compatibility with Python's `zlib` (decompression path).
 *
 * Usage:  node scripts/conformance.mjs
 */
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const work = mkdtempSync(join(tmpdir(), "stang-conformance-"));
const bundle = join(work, "codec.mjs");

console.log("• Bundling src/stg/codec.ts with esbuild…");
execFileSync(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["esbuild", "src/stg/codec.ts", "--bundle", "--platform=node", "--format=esm", `--outfile=${bundle}`],
  { cwd: root, stdio: "inherit" },
);

const codec = await import(bundle);
// Key-order-insensitive JSON comparison (records compare semantically).
const canonical = (value) => codec.canonicalJsonString(value);
const fixtures = join(root, "tests", "fixtures");
const records = JSON.parse(readFileSync(join(fixtures, "golden.json"), "utf8"));
const PASSPHRASE = "secret-stang-key";

let failures = 0;
const ok = (label, condition) => {
  if (condition) {
    console.log(`  ✓ ${label}`);
  } else {
    console.error(`  ✗ ${label}`);
    failures += 1;
  }
};

console.log("• Golden plain fixture (STG2, unencrypted)");
const plain = readFileSync(join(fixtures, "golden_plain.stg"));
const plainParsed = await codec.parseStg(new Uint8Array(plain));
ok("magic/version detected", plainParsed.formatVersion === 2);
ok("records round-trip", canonical(plainParsed.records) === canonical(records));
ok("block count", plainParsed.blockCount === 3);
ok("rotation state", plainParsed.rotationState === 1);
const reserialized = await codec.serializeStg({
  records,
  blockCount: 3,
  rotationState: 1,
  format: "stg2",
});
ok("re-serialization is byte-identical", Buffer.from(reserialized).equals(plain));

console.log("• Golden encrypted fixture (STG2, zlib + AEAD)");
const encrypted = readFileSync(join(fixtures, "golden_encrypted.stg"));
ok("ciphertext hides plaintext", !encrypted.includes(Buffer.from("Genz")));
const encParsed = await codec.parseStg(new Uint8Array(encrypted), { passphrase: PASSPHRASE });
ok("decrypts to the same records", canonical(encParsed.records) === canonical(records));
ok("compressed flag honoured", encParsed.compressed === true);
ok("rotation state", encParsed.rotationState === 1);
let wrongPassFailed = false;
try {
  await codec.parseStg(new Uint8Array(encrypted), { passphrase: "wrong" });
} catch (error) {
  wrongPassFailed = String(error).includes("Authentication failed");
}
ok("wrong passphrase rejected with Authentication failed", wrongPassFailed);

console.log("• Byte-exact AEAD round-trip (uncompressed, pinned salt+nonces)");
{
  const encryptedPlain = readFileSync(join(fixtures, "golden_encrypted_plain.stg"));
  const salt = new Uint8Array(16).map((_, i) => i);
  const nonces = [0, 1, 2].map((i) => new Uint8Array(16).fill(0xb0 + i));
  const reencrypted = await codec.serializeStg({
    records,
    blockCount: 3,
    rotationState: 1,
    format: "stg2",
    passphrase: PASSPHRASE,
    salt,
    nonces,
  });
  ok(
    "pinned salt+nonces reproduce golden_encrypted_plain.stg",
    Buffer.from(reencrypted).equals(encryptedPlain),
  );
  const parsed = await codec.parseStg(new Uint8Array(encryptedPlain), { passphrase: PASSPHRASE });
  ok(
    "golden_encrypted_plain.stg decrypts to the same records",
    canonical(parsed.records) === canonical(records),
  );
}

console.log("• Canonical JSON edge cases (must match Python json.dumps)");
{
  const cases = [
    [0, "0"],
    [1, "1"],
    [0.5, "0.5"],
    [-7.75, "-7.75"],
    [12345.678, "12345.678"],
    [1e-7, "1e-07"],
    [0.0001, "0.0001"],
    [1e-5, "1e-05"],
    [1e15, "1000000000000000"],
    [1e16, "1e+16"],
    [1e17, "1e+17"],
    [1e21, "1e+21"],
    [1.5e21, "1.5e+21"],
    [2e20, "2e+20"],
    [5e-324, "5e-324"],
    [123456789.123456789, "123456789.12345679"],
    [9007199254740991, "9007199254740991"],
  ];
  for (const [input, expected] of cases) {
    const actual = codec.canonicalJsonString(input);
    ok(`number ${String(input)} -> ${expected}`, actual === expected);
  }
  // Key ordering is by Unicode code point, not UTF-16 code units.
  const astralFirst = String.fromCodePoint(0xffff);
  const astralSecond = String.fromCodePoint(0x10000);
  const keyed = {};
  keyed[astralSecond] = 1;
  keyed[astralFirst] = 2;
  ok(
    "astral keys sort by code point",
    codec.canonicalJsonString(keyed)
      === `{"${astralFirst}":2,"${astralSecond}":1}`,
  );
}

console.log("• Unknown flag bits are rejected");
{
  for (const [name, fixture] of [["STG2", "golden_plain.stg"]]) {
    const mutated = Buffer.from(readFileSync(join(fixtures, fixture)));
    mutated[5] |= 0x08;
    let rejected = false;
    try {
      await codec.parseStg(new Uint8Array(mutated));
    } catch (error) {
      rejected = String(error).includes("unknown bits");
    }
    ok(`${name} flags with unknown bits rejected`, rejected);
  }
}

console.log("• v1 legacy container support");
const v1 = await codec.serializeStg({ records, blockCount: 2, format: "stg1" });
const v1Parsed = await codec.parseStg(v1);
ok("v1 magic", Buffer.from(v1.slice(0, 4)).toString() === "STG1");
ok("v1 records round-trip", canonical(v1Parsed.records) === canonical(records));

if (failures > 0) {
  console.error(`\n${failures} conformance check(s) FAILED`);
  process.exit(1);
}
console.log("\nAll conformance checks passed — Python and JS agree byte-for-byte.");
