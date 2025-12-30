import { useTranslation } from "react-i18next";
import { BiHide, BiShow } from "react-icons/bi";

// Reusable Password Field
const PasswordField = ({
  label,
  value,
  onChange,
  onBlur,
  placeholder,
  error,
  showPassword,
  setShowPassword,
  isRTL,
  containerClassName = "",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur: (e: React.FocusEvent<HTMLInputElement>) => void;
  placeholder: string;
  error?: string;
  showPassword: boolean;
  setShowPassword: (val: boolean) => void;
  isRTL: boolean;
  containerClassName?: string;
}) => {
  const { t } = useTranslation("discoveryPage");

  return (
    <div className={containerClassName}>
      <label className="block text-xs font-medium text-neutral-50 mb-1.5">
        {label}
      </label>
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          placeholder={placeholder}
          className="w-full bg-neutral-900/50 border border-neutral-600 focus:border-secondary-500 focus:ring-1 focus:ring-secondary-500/20 rounded-lg px-3 py-2 text-sm text-neutral-50 placeholder-neutral-500 transition-all outline-none"
        />
        <button
          type="button"
          onPointerDown={(e) => {
            setShowPassword(true);
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerUp={() => setShowPassword(false)}
          onPointerCancel={() => setShowPassword(false)}
          className={`absolute ${isRTL ? "left-2" : "right-2"} top-1/2 -translate-y-1/2 text-neutral-300 pointer-events-auto w-4 h-4`}
        >
          {showPassword ? <BiHide /> : <BiShow />}
        </button>
      </div>
      {error && (
        <p className="text-red-500 text-xs mt-1">
          {t(`manualDiscovery.errors.${error}`)}
        </p>
      )}
    </div>
  );
};

export default PasswordField;
