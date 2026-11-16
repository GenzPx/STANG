interface LogoProps {
  size?: number;
  className?: string;
  animated?: boolean;
}

/** STANG mark: four rotational arc segments around a core. */
export function Logo({ size = 34, className = "", animated = false }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={`${className} ${animated ? "spin-slow" : ""}`}
      role="img"
      aria-label="STANG logo"
    >
      <circle cx="16" cy="16" r="15" fill="#0b0f17" stroke="rgba(34,211,238,0.35)" strokeWidth="1" />
      <g
        fill="none"
        stroke="url(#stang-arc)"
        strokeWidth="2.6"
        strokeLinecap="round"
      >
        <path d="M16 4a12 12 0 0 1 10.4 6" />
        <path d="M28 16a12 12 0 0 1-6 10.4" />
        <path d="M16 28A12 12 0 0 1 5.6 22" />
        <path d="M4 16A12 12 0 0 1 10 5.6" />
      </g>
      <circle cx="16" cy="16" r="3.4" fill="url(#stang-core)" />
      <defs>
        <linearGradient id="stang-arc" x1="4" y1="4" x2="28" y2="28">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#34d399" />
        </linearGradient>
        <radialGradient id="stang-core" cx="0.5" cy="0.5" r="0.6">
          <stop offset="0" stopColor="#6ee7b7" />
          <stop offset="1" stopColor="#059669" />
        </radialGradient>
      </defs>
    </svg>
  );
}
