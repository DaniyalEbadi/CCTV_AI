import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { BiChevronDown } from "react-icons/bi";

// Reusable Select Field with Custom Dropdown
type SelectOption = { value: string; label: string };

const SelectField = ({
  label,
  value,
  onChange,
  onBlur,
  options,
  placeholderOption,
  error,
  required = false,
  isRTL,
  containerClassName = "",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onBlur: (e: React.FocusEvent<HTMLSelectElement>) => void;
  options: SelectOption[];
  placeholderOption: string;
  error?: string;
  required?: boolean;
  isRTL: boolean;
  containerClassName?: string;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        // Simulate blur event when closing via outside click
        const syntheticBlurEvent = {
          target: { value },
        } as React.FocusEvent<HTMLSelectElement>;
        onBlur(syntheticBlurEvent);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onBlur, value]);

  const handleOptionClick = (opt: SelectOption) => {
    const syntheticChangeEvent = {
      target: { value: opt.value },
    } as React.ChangeEvent<HTMLSelectElement>;
    onChange(syntheticChangeEvent);
    setIsOpen(false);
    // Simulate blur after selection
    const syntheticBlurEvent = {
      target: { value: opt.value },
    } as React.FocusEvent<HTMLSelectElement>;
    onBlur(syntheticBlurEvent);
  };

  const selectedLabel =
    options.find((opt) => opt.value === value)?.label || placeholderOption;

  const { t } = useTranslation("discoveryPage");

  return (
    <div className={containerClassName}>
      <label className="block text-xs font-medium text-neutral-50 mb-1.5">
        {label} {required && <span className="text-secondary-400">*</span>}
      </label>
      <div className="relative" ref={containerRef}>
        {/* Trigger button */}
        <div
          className={`w-full bg-neutral-900/50 border ${
            error ? "border-red-500" : "border-neutral-600"
          } focus:border-secondary-500 focus:ring-1 focus:ring-secondary-500/20 rounded-lg px-3 py-2 text-sm text-neutral-50 cursor-pointer transition-all outline-none flex items-center justify-between`}
          onClick={() => setIsOpen(!isOpen)}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setIsOpen(!isOpen);
            }
          }}
          dir={isRTL ? "rtl" : "ltr"}
        >
          <span className={value ? "text-neutral-50" : "text-neutral-300"}>
            {selectedLabel}
          </span>
          <BiChevronDown
            className={`text-neutral-300 w-4 h-4 transition-transform ${isOpen ? "rotate-180" : "rotate-0"}`}
          />
        </div>

        {/* Custom dropdown menu */}
        {isOpen && (
          <div
            className={`absolute ${
              isRTL ? "right-0 origin-top-right" : "left-0 origin-top-left"
            } z-10 mt-1 w-full bg-neutral-800 border border-neutral-600 rounded-lg shadow-lg max-h-60 overflow-y-auto`}
            dir={isRTL ? "rtl" : "ltr"}
          >
            {options.map((opt) => (
              <div
                key={opt.value}
                className={`px-3 py-2 text-sm cursor-pointer transition-colors ${
                  opt.value === value
                    ? "bg-secondary-500/20 text-secondary-300"
                    : "text-neutral-50 hover:bg-neutral-700"
                }`}
                onClick={() => handleOptionClick(opt)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleOptionClick(opt);
                  }
                }}
                tabIndex={0}
                role="option"
                aria-selected={opt.value === value}
              >
                {opt.label}
              </div>
            ))}
          </div>
        )}
      </div>
      {error && (
        <p className="text-red-500 text-xs mt-1">
          {t(`manualDiscovery.errors.${error}`)}
        </p>
      )}
    </div>
  );
};

export default SelectField;
