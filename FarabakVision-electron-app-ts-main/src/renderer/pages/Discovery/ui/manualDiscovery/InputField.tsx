import { useTranslation } from "react-i18next";

// Reusable Input Field
const InputField = ({
  label,
  value,
  onChange,
  onBlur,
  placeholder,
  error,
  required = false,
  type = "text",
  className = "",
  containerClassName = "",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur: (e: React.FocusEvent<HTMLInputElement>) => void;
  placeholder: string;
  error?: string;
  required?: boolean;
  type?: string;
  className?: string;
  containerClassName?: string;
}) => {
  const { t } = useTranslation("discoveryPage");

  return (
    <div className={containerClassName}>
      <label className="block text-xs font-medium text-neutral-50 mb-1.5">
        {label} {required && <span className="text-secondary-400">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        placeholder={placeholder}
        className={`w-full bg-neutral-900/50 border border-neutral-600 focus:border-secondary-500 focus:ring-1 focus:ring-secondary-500/20 rounded-lg px-3 py-2 text-sm text-neutral-50 placeholder-neutral-500 transition-all outline-none ${className}`}
      />
      {error && (
        <p className="text-red-500 text-xs mt-1">
          {t(`manualDiscovery.errors.${error}`)}
        </p>
      )}
    </div>
  );
};
export default InputField;
