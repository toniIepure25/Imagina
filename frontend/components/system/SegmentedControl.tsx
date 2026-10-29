"use client";

type Option<T extends string> = {
  id: T;
  label: string;
};

export default function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  className = "",
}: {
  label: string;
  options: ReadonlyArray<Option<T>>;
  value: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  return (
    <div role="group" aria-label={label} className={`flex items-center gap-1 ${className}`}>
      {options.map((option) => {
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.id)}
            className={`min-h-9 border px-3 text-[11px] transition-colors ${
              active
                ? "border-lumen-mint/35 bg-lumen-mint/[0.08] text-lumen-mint"
                : "border-transparent text-foreground/40 hover:border-white/10 hover:text-foreground/75"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
