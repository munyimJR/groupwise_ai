"use client";

import { useTaxonomy } from "@/lib/queries";

export function CategorySelect({ value, onChange, id = "category" }: { value: string; onChange: (v: string) => void; id?: string }) {
  const { data } = useTaxonomy();
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 w-full rounded-lg border border-input bg-white px-3 text-sm text-ink"
    >
      {!data && <option value={value}>Loading categories…</option>}
      {data?.map((c) => (
        <optgroup key={c.category} label={c.category}>
          {c.subcategories.map((s) => (
            <option key={s.key} value={s.key}>
              {c.category} › {s.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
