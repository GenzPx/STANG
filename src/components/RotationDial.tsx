import { useId } from "react";

interface RotationDialProps {
  count: number;
  value: number;
  onChange?: (value: number) => void;
  size?: number;
  disabled?: boolean;
}

const TAU = Math.PI * 2;

function polar(cx: number, cy: number, radius: number, angle: number): [number, number] {
  return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
}

/** Arc path for one segment of the dial. */
function arcSegment(
  cx: number,
  cy: number,
  outer: number,
  inner: number,
  startAngle: number,
  endAngle: number,
): string {
  const [ox1, oy1] = polar(cx, cy, outer, startAngle);
  const [ox2, oy2] = polar(cx, cy, outer, endAngle);
  const [ix2, iy2] = polar(cx, cy, inner, endAngle);
  const [ix1, iy1] = polar(cx, cy, inner, startAngle);
  const large = endAngle - startAngle > Math.PI ? 1 : 0;
  return [
    `M ${ox1.toFixed(3)} ${oy1.toFixed(3)}`,
    `A ${outer} ${outer} 0 ${large} 1 ${ox2.toFixed(3)} ${oy2.toFixed(3)}`,
    `L ${ix2.toFixed(3)} ${iy2.toFixed(3)}`,
    `A ${inner} ${inner} 0 ${large} 0 ${ix1.toFixed(3)} ${iy1.toFixed(3)}`,
    "Z",
  ].join(" ");
}

/**
 * Interactive rotational dial. STANG never moves data physically; the dial
 * visualises the logical rotation state stored in the container header.
 */
export function RotationDial({
  count,
  value,
  onChange,
  size = 132,
  disabled = false,
}: RotationDialProps) {
  const id = useId();
  const center = 50;
  const outer = 44;
  const inner = 26;
  const gap = 0.035; // radians of separation between segments
  const safeCount = Math.max(1, count);
  const step = TAU / safeCount;
  const segments = Array.from({ length: safeCount }, (_, index) => {
    const start = -Math.PI / 2 + index * step + gap;
    const end = -Math.PI / 2 + (index + 1) * step - gap;
    return { index, d: arcSegment(center, center, outer, inner, start, end) };
  });

  const [needleX, needleY] = polar(
    center,
    center,
    inner - 6,
    -Math.PI / 2 + (value + 0.5) * step,
  );

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="slider"
      aria-valuemin={0}
      aria-valuemax={safeCount - 1}
      aria-valuenow={value}
      aria-label="Rotation state"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(event) => {
        if (disabled || !onChange) return;
        if (event.key === "ArrowRight" || event.key === "ArrowUp") {
          onChange((value + 1) % safeCount);
          event.preventDefault();
        } else if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
          onChange((value - 1 + safeCount) % safeCount);
          event.preventDefault();
        }
      }}
      className="outline-none focus-visible:ring-2 ring-cyan-400/60 rounded-full select-none"
    >
      <defs>
        <linearGradient id={`${id}-active`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#34d399" />
        </linearGradient>
      </defs>
      <circle cx={center} cy={center} r={inner - 10} fill="rgba(2,6,23,0.7)" stroke="rgba(148,163,184,0.25)" strokeWidth="0.6" />
      {segments.map(({ index, d }) => {
        const active = index === value;
        return (
          <path
            key={index}
            d={d}
            className="dial-segment"
            fill={active ? `url(#${id}-active)` : "rgba(100,116,139,0.32)"}
            opacity={disabled ? 0.55 : 1}
            onClick={() => !disabled && onChange?.(index)}
          >
            <title>
              Block {index}
              {active ? " — current rotation position" : ""}
            </title>
          </path>
        );
      })}
      <line
        x1={center}
        y1={center}
        x2={needleX}
        y2={needleY}
        stroke="#67e8f9"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.9"
        style={{ transition: "all 240ms ease" }}
      />
      <circle cx={center} cy={center} r={2.4} fill="#67e8f9" />
      <text
        x={center}
        y={center + 8.5}
        textAnchor="middle"
        fontSize="8.5"
        fontWeight={700}
        fill="#e2e8f0"
        className="font-mono2"
      >
        {value}
      </text>
    </svg>
  );
}
