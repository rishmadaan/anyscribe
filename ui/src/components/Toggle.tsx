export default function Toggle({
  value,
  onChange,
  label,
  disabled,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <button
      role="switch"
      aria-checked={value}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!value)}
      className={`w-9 h-5 rounded-full transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
        value ? "bg-amber" : "bg-border"
      }`}
    >
      <div
        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
          value ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}
