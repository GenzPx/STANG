/** Sample datasets for the STANG studio playground. */

export interface SampleDataset {
  id: string;
  label: string;
  hint: string;
  records: Record<string, unknown>[];
}

export const SAMPLE_DATASETS: SampleDataset[] = [
  {
    id: "orders",
    label: "Sales orders",
    hint: "Nested documents with arrays and nulls",
    records: [
      { sku: "STG-001", product: "Rotational Drive", qty: 4, price: 129.5, currency: "USD", priority: true, meta: { warehouse: "JKT-01", bin: "A7" } },
      { sku: "STG-114", product: "Logical Spindle", qty: 2, price: 340.0, currency: "USD", priority: false, meta: { warehouse: "JKT-03", bin: "C2" } },
      { sku: "STG-220", product: "Rotation Bearing", qty: 12, price: 18.75, currency: "EUR", priority: false, meta: { warehouse: "SBY-02", bin: "B1" } },
      { sku: "STG-317", product: "Circular Encoder", qty: 1, price: 980.0, currency: "USD", priority: true, meta: { warehouse: "JKT-01", bin: "D4" } },
      { sku: "STG-402", product: "Offset Coupling", qty: 7, price: 42.1, currency: "EUR", priority: false, meta: { warehouse: "MLG-01", bin: "A1" } },
      { sku: "STG-518", product: "Vector Cam", qty: 3, price: 275.25, currency: "USD", priority: true, meta: { warehouse: "JKT-03", bin: "C9" } },
    ],
  },
  {
    id: "iot",
    label: "IoT sensor readings",
    hint: "Flat records — ideal for watching block distribution",
    records: Array.from({ length: 24 }, (_, index) => ({
      sensor: `TRH-${String(index % 6).padStart(3, "0")}`,
      temperature: Number((24 + Math.sin(index * 1.7) * 6).toFixed(2)),
      humidity: Number((55 + Math.cos(index * 1.3) * 18).toFixed(2)),
      battery: 4.2 - (index % 24) * 0.02,
      online: index % 7 !== 0,
    })),
  },
  {
    id: "profiles",
    label: "Mixed profiles",
    hint: "Booleans, floats, arrays, nulls, unicode",
    records: [
      { id: 1, name: "Genz", active: true, score: 9.5, note: null, tags: ["core", "maintainer"], meta: { city: "Jakarta" } },
      { id: 2, name: "Ana", active: false, score: 3.25, note: "on leave", tags: [], meta: { city: "Bandung" } },
      { id: 3, name: "Budi", active: true, score: 7, note: "héllo wörld", tags: ["contributor"], meta: { city: "Surabaya" } },
      { id: 4, name: "Citra", active: true, score: 8.75, note: "", tags: ["triage"], meta: { city: "Denpasar" } },
    ],
  },
  {
    id: "basic",
    label: "Minimal pair",
    hint: "The original examples/basic records",
    records: [
      { id: 1, name: "Genz", value: "example" },
      { id: 2, name: "Ana", value: "sample" },
    ],
  },
];
