import { useState } from "react";
import { ExternalLink, ScrollText } from "lucide-react";
import { Logo } from "./components/Logo";
import { EncodePanel } from "./components/EncodePanel";
import { DecodePanel } from "./components/DecodePanel";
import { SpecPanel } from "./components/SpecPanel";
import { CliPanel } from "./components/CliPanel";

const TABS = [
  { id: "encode", label: "Encode" },
  { id: "decode", label: "Decode & Inspect" },
  { id: "format", label: "Format Guide" },
  { id: "cli", label: "CLI Reference" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("encode");

  return (
    <div className="min-h-full">
      <div className="app-ambient" aria-hidden="true" />

      {/* ------------------------------- Header ------------------------------ */}
      <header className="sticky top-0 z-30 border-b border-slate-800/70 bg-[#0b0f17]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-3 px-4 py-2.5 sm:px-6">
          <a href="#" onClick={(event) => event.preventDefault()} className="flex items-center gap-2.5">
            <Logo size={36} animated />
            <div className="leading-tight">
              <div className="flex items-center gap-2">
                <span className="text-[1.05rem] font-black tracking-[0.22em] text-slate-100">
                  STANG
                </span>
                <span className="chip chip-info !py-0.5">v2.1.0</span>
              </div>
              <div className="text-[0.58rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Rotational Data Container
              </div>
            </div>
          </a>

          <nav className="order-3 -mx-1 flex w-full items-center gap-1 overflow-x-auto nice-scroll pt-2 sm:order-2 sm:w-auto sm:pt-0 md:mx-auto" aria-label="Studio sections">
            {TABS.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="tab-button"
                data-active={tab === entry.id}
                onClick={() => setTab(entry.id)}
                aria-pressed={tab === entry.id}
              >
                {entry.label}
              </button>
            ))}
          </nav>

          <div className="order-2 ml-auto flex items-center gap-2 sm:order-3 sm:ml-0">
            <span className="hidden items-center gap-1.5 text-[0.62rem] font-semibold uppercase tracking-widest text-emerald-400 md:flex">
              <span className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
              in-browser codec
            </span>
            <a
              className="btn btn-ghost btn-sm"
              href="https://github.com/GenzPx/STANG"
              target="_blank"
              rel="noreferrer noopener"
            >
              <ExternalLink size={13} />
              <span className="hidden sm:inline">GenzPx/STANG</span>
            </a>
          </div>
        </div>
      </header>

      {/* -------------------------------- Main ------------------------------- */}
      <main className="mx-auto max-w-[1440px] px-4 pb-10 pt-5 sm:px-6">
        {/* Hero strip */}
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-black leading-tight text-slate-100 sm:text-[1.7rem]">
              The container that{" "}
              <span className="bg-gradient-to-r from-cyan-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                turns instead of walking
              </span>
            </h1>
            <p className="mt-1 max-w-2xl text-[0.78rem] leading-relaxed text-slate-400">
              Encode, seal, rotate and decode{" "}
              <code className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono2 text-[0.7rem] text-cyan-300">
                .stg
              </code>{" "}
              containers with a byte-compatible implementation — the same bytes the Python CLI
              writes, produced right here in your browser.
            </p>
          </div>
          <div className="flex items-center gap-2 text-[0.62rem] font-semibold uppercase tracking-widest text-slate-500">
            <ScrollText size={12} />
            STG1 &amp; STG2 byte-compatible
          </div>
        </div>

        <div hidden={tab !== "encode"}>
          <EncodePanel />
        </div>
        <div hidden={tab !== "decode"}>
          <DecodePanel />
        </div>
        <div hidden={tab !== "format"}>
          <SpecPanel />
        </div>
        <div hidden={tab !== "cli"}>
          <CliPanel />
        </div>
      </main>

      {/* -------------------------------- Footer ------------------------------ */}
      <footer className="border-t border-slate-800/70 bg-[#0b0f17]/70">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-4 text-[0.65rem] text-slate-500 sm:px-6">
          <div className="flex items-center gap-2">
            <Logo size={18} />
            <span>
              <span className="font-bold text-slate-300">STANG</span> — a rotational data
              container. Not a database.
            </span>
          </div>
          <div className="font-mono2">
            STG2 current · STG1 legacy · PBKDF2 + HMAC-SHA256 · zlib · all rights reserved
          </div>
        </div>
      </footer>
    </div>
  );
}
