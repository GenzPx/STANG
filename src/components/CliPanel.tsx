import { useState } from "react";
import { Check, Copy, Terminal, KeyRound, ListOrdered, CircleAlert } from "lucide-react";

const COMMANDS: { name: string; synopsis: string; description: string; example: string }[] = [
  {
    name: "stang init",
    synopsis: "stang init FILE [--blocks N] [--compress] [--encrypt] [--hmac] [--format stg1|stg2]",
    description: "Create an empty STG container (defaults: 4 blocks, STG2).",
    example: "stang init ledger.stg --blocks 8 --compress",
  },
  {
    name: "stang encode",
    synopsis: "stang encode INPUT.json OUTPUT.stg [--blocks N] [--rotation N] [--compress] [--encrypt] [--hmac] [--format stg1|stg2]",
    description: "Encode a JSON object/array into a .stg container. '-' reads stdin / writes stdout.",
    example: "stang encode orders.json orders.stg --blocks 8 --compress --rotation 3",
  },
  {
    name: "stang decode",
    synopsis: "stang decode INPUT.stg OUTPUT.json [--pretty]",
    description: "Decode records back to JSON. Output is canonical: decode(encode(x)) == x.",
    example: "stang decode orders.stg orders.out.json --pretty",
  },
  {
    name: "stang dump",
    synopsis: "stang dump INPUT.stg [--format block|json|ndjson|csv|tsv|markdown|stats|raw]",
    description: "Render records with a dumper plugin — from human blocks to NDJSON or Markdown tables.",
    example: "stang dump orders.stg --format markdown",
  },
  {
    name: "stang inspect",
    synopsis: "stang inspect INPUT.stg [--json]",
    description: "Header metadata without full decode: format, flags, blocks, schema, verification state.",
    example: "stang inspect orders.stg --json | jq .rotation_state",
  },
  {
    name: "stang rotate",
    synopsis: "stang rotate INPUT.stg OFFSET",
    description: "Bump the logical rotation state by OFFSET (negative turns backwards). Never moves bytes.",
    example: "stang rotate orders.stg +2",
  },
  {
    name: "stang verify",
    synopsis: "stang verify INPUT.stg",
    description: "Authenticate the container. Exit 0 = valid, 1 = invalid, 2 = credentials required.",
    example: "stang verify orders.stg && echo sealed",
  },
  {
    name: "stang convert",
    synopsis: "stang convert INPUT.stg OUTPUT.stg --to stg1|stg2",
    description: "Re-wrap between wire formats. STG2→STG1 refuses to drop compression or crypto.",
    example: "stang convert legacy.stg current.stg --to stg2",
  },
  {
    name: "stang keygen",
    synopsis: "stang keygen [--bytes N] [--hex]",
    description: "Generate a high-entropy random passphrase for --encrypt, printed to stdout.",
    example: "stang keygen",
  },
  {
    name: "stang status",
    synopsis: "stang status",
    description: "Runtime summary: version, Python, crypto suite and supported formats.",
    example: "stang status",
  },
];

const SESSION = `$ stang encode input.json data.stg --blocks 4 --compress
Encoded input.json -> data.stg
  format=STG2 blocks=4 rotation=0 records=2 size=233B [zlib(312B->blocks)]
$ stang inspect data.stg
File       : data.stg
Magic      : STG2
Format     : STG2
Blocks     : 4
Rotation   : 0
Records    : 2
Flags      : compressed
Schema     : {'active': 'boolean', 'id': 'integer', 'name': 'string'}
Checksum   : VALID
$ stang rotate data.stg +1
Rotated data.stg to state 1
$ stang verify data.stg
data.stg: VALID`;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm !px-2"
      aria-label="Copy to clipboard"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        } catch {
          /* clipboard unavailable */
        }
      }}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}

export function CliPanel() {
  return (
    <div className="grid gap-5 xl:grid-cols-[7fr_5fr]">
      <section className="panel p-5">
        <div className="mb-3 flex items-center gap-2">
          <Terminal size={16} className="text-cyan-300" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100">COMMAND REFERENCE</h2>
        </div>
        <div className="space-y-2.5">
          {COMMANDS.map((command) => (
            <div
              key={command.name}
              className="rounded-xl border border-slate-800 bg-slate-950/50 p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <code className="font-mono2 text-[0.78rem] font-bold text-emerald-300">
                  {command.name}
                </code>
                <CopyButton text={command.example} />
              </div>
              <p className="mt-1 text-[0.7rem] leading-relaxed text-slate-400">
                {command.description}
              </p>
              <code className="mt-1.5 block overflow-x-auto nice-scroll whitespace-nowrap font-mono2 text-[0.65rem] text-slate-500">
                {command.synopsis}
              </code>
            </div>
          ))}
        </div>
      </section>

      <div className="flex flex-col gap-5">
        <section className="panel p-5">
          <div className="mb-2 flex items-center gap-2">
            <Terminal size={16} className="text-emerald-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">A TYPICAL SESSION</h2>
          </div>
          <pre className="terminal overflow-x-auto nice-scroll p-4">
            {SESSION.split("\n").map((line, index) => {
              if (line.startsWith("$ ")) {
                return (
                  <div key={index}>
                    <span className="prompt">$ </span>
                    <span className="text-slate-100">{line.slice(2)}</span>
                  </div>
                );
              }
              return (
                <div key={index} className="out">
                  {line}
                </div>
              );
            })}
          </pre>
        </section>

        <section className="panel p-5">
          <div className="mb-2 flex items-center gap-2">
            <KeyRound size={16} className="text-violet-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">CREDENTIALS, DONE RIGHT</h2>
          </div>
          <p className="text-[0.72rem] leading-relaxed text-slate-400">
            Secrets never belong on the command line. Pass them through flags pointing at the
            environment or a file — the CLI prompts interactively when neither is given.
          </p>
          <table className="data-table mt-3">
            <thead>
              <tr><th>Flag</th><th>Meaning</th></tr>
            </thead>
            <tbody>
              <tr><td>--passphrase-env VAR</td><td>Read passphrase from env var VAR</td></tr>
              <tr><td>--passphrase-file PATH</td><td>Read passphrase from file (newline stripped)</td></tr>
              <tr><td>--key-env VAR</td><td>Read raw HMAC integrity key from env var</td></tr>
              <tr><td>--key-file PATH</td><td>Read raw integrity key bytes from file</td></tr>
            </tbody>
          </table>
          <pre className="terminal mt-3 overflow-x-auto nice-scroll p-3 text-[0.68rem]">
{`export STANG_PASSPHRASE="$(stang keygen)"
stang encode data.json data.stg --encrypt --passphrase-env STANG_PASSPHRASE
stang decode data.stg data.json --passphrase-env STANG_PASSPHRASE`}
          </pre>
        </section>

        <section className="panel p-5">
          <div className="mb-2 flex items-center gap-2">
            <ListOrdered size={16} className="text-amber-300" />
            <h2 className="text-sm font-bold tracking-wide text-slate-100">EXIT CODES</h2>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Code</th><th>Meaning</th></tr>
            </thead>
            <tbody>
              <tr><td>0</td><td>Success (or container is VALID for verify)</td></tr>
              <tr><td>1</td><td>Failure: malformed file, bad credentials, I/O error</td></tr>
              <tr><td>2</td><td>verify only: container is encrypted/keyed, credentials required</td></tr>
            </tbody>
          </table>
        </section>

        <section className="panel p-5">
          <div className="mb-1.5 flex items-center gap-2 text-[0.72rem] font-bold uppercase tracking-widest text-slate-500">
            <CircleAlert size={12} /> Good to know
          </div>
          <ul className="list-disc space-y-1 pl-4 text-[0.72rem] leading-relaxed text-slate-400">
            <li><code className="font-mono2 text-slate-300">stang dump --format stats</code> shows how records spread across blocks.</li>
            <li>Pipe through stdin/stdout with <code className="font-mono2 text-slate-300">-</code>: <code className="font-mono2 text-slate-300">cat data.stg | stang inspect -</code>.</li>
            <li>Every command is safe on encrypted files — pass <code className="font-mono2 text-slate-300">--passphrase-env</code> and the CLI handles re-encryption transparently.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
