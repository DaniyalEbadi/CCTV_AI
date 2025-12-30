// Reusable Toggle Buttons (for transport)
const ToggleButtons = ({
  label,
  options,
  value,
  onChange,
  containerClassName = "",
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (val: string) => void;
  containerClassName?: string;
}) => (
  <div className={containerClassName}>
    <label className="block text-xs font-medium text-neutral-50 mb-1.5">
      {label}
    </label>
    <div className="flex gap-2 w-full">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`flex-1 px-5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            value === opt
              ? "bg-secondary-500 text-neutral-900 shadow-lg shadow-secondary-500/25"
              : "bg-neutral-700 text-neutral-300 hover:bg-neutral-600"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  </div>
);
export default ToggleButtons;
