import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BiPlus, BiInfoCircle } from "react-icons/bi";
import { FaRegKeyboard } from "react-icons/fa";
import SectionHeader from "./SectionHeader";
import InputField from "./InputField";
import SelectField from "./SelectField";
import ToggleButtons from "./ToggleButtons";
import PasswordField from "./PasswordField";

const ManualDiscovery = () => {
  const { t, i18n } = useTranslation("discoveryPage");
  const isRTL = i18n.dir() === "rtl";

  const [ipAddress, setIpAddress] = useState("");
  const [port, setPort] = useState("554");
  const [cameraName, setCameraName] = useState("");
  const [category, setCategory] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [brand, setBrand] = useState("");
  const [protocol, setProtocol] = useState("RTSP");
  const [transportProtocol, setTransportProtocol] = useState<"TCP" | "UDP">(
    "TCP"
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const categories = ["Indoor", "Outdoor", "PTZ", "Dome", "Bullet", "Other"];
  const brands = [
    "Reolink",
    "Hikvision",
    "Dahua",
    "Axis",
    "Bosch",
    "Sony",
    "Other",
  ];
  const protocols = ["RTSP", "ONVIF"];

  const categoryOptions = categories.map((cat) => ({
    value: cat,
    label: t(`manualDiscovery.categories.${cat}`),
  }));
  const brandOptions = brands.map((b) => ({
    value: b,
    label: t(`manualDiscovery.brands.${b}`),
  }));
  const protocolOptions = protocols.map((p) => ({
    value: p,
    label: t(`manualDiscovery.protocols.${p}`),
  }));

  const isSafeInput = (value: string) => {
    // Basic check for potential XSS/SQL injection characters
    const forbiddenPattern = /[<>'";-]/;
    return !forbiddenPattern.test(value);
  };

  const validateField = (name: string, value: string) => {
    let error = "";

    if (
      [
        "cameraName",
        "category",
        "brand",
        "ipAddress",
        "port",
        "protocol",
        "username",
      ].includes(name)
    ) {
      if (!value.trim()) {
        error = "required";
      }
    }

    if (name === "cameraName" || name === "username" || name === "password") {
      if (value && !isSafeInput(value)) {
        error = "invalidCharacters";
      }
    }

    if (name === "ipAddress") {
      if (value && !isSafeInput(value)) {
        error = "invalidCharacters";
      } else if (value) {
        const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
        if (!ipRegex.test(value)) {
          error = "invalidIp";
        } else {
          const parts = value.split(".").map(Number);
          if (parts.some((p) => p < 0 || p > 255 || isNaN(p))) {
            error = "invalidIp";
          }
        }
      }
    }

    if (name === "port") {
      if (value && !isSafeInput(value)) {
        error = "invalidCharacters";
      } else if (value) {
        const portRegex = /^\d+$/;
        if (!portRegex.test(value)) {
          error = "invalidPort";
        } else {
          const portNum = parseInt(value, 10);
          if (portNum < 0 || portNum > 65535) {
            error = "invalidPort";
          }
        }
      }
    }

    setErrors((prev) => ({ ...prev, [name]: error }));
    return error;
  };

  const handleBlur = (
    name: string,
    e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    validateField(name, e.target.value);
  };

  const validateAll = () => {
    const fields = {
      cameraName,
      category,
      brand,
      ipAddress,
      port,
      protocol,
      username,
    };

    const newErrors: Record<string, string> = {};
    let isValid = true;

    Object.entries(fields).forEach(([name, value]) => {
      const error = validateField(name, value);
      if (error) {
        newErrors[name] = error;
        isValid = false;
      }
    });

    // Optional password check
    if (password && !isSafeInput(password)) {
      newErrors.password = "invalidCharacters";
      isValid = false;
    }

    setErrors((prev) => ({ ...prev, ...newErrors }));
    return isValid;
  };

  const handleAdd = async () => {
    if (!validateAll()) {
      return;
    }

    setIsSubmitting(true);
    // TODO: Implement actual submit logic here, e.g., API call
    console.log({
      ipAddress,
      port,
      cameraName,
      category,
      username,
      password,
      brand,
      protocol,
      transportProtocol,
    });
    // Simulate submission
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsSubmitting(false);
  };

  const hasErrors =
    Object.values(errors).some((e) => e) ||
    !cameraName ||
    !category ||
    !brand ||
    !ipAddress ||
    !port ||
    !protocol ||
    !username;

  return (
    <div className="w-full h-fit flex flex-col animate-fade-in">
      {/* Compact Header */}
      <div className="bg-linear-to-br from-secondary-500/30 to-secondary-600/30 border border-secondary-600 rounded-2xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-secondary-500/20 rounded-xl">
            <FaRegKeyboard className="w-6 h-6 text-secondary-300" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-neutral-50 mb-2">
              {t("manualDiscovery.header.title")}
            </h2>
            <p className="text-neutral-300 text-sm leading-relaxed">
              {t("manualDiscovery.header.description")}
            </p>
          </div>
        </div>
      </div>

      {/* Main Form Card */}
      <div className="flex-1 bg-neutral-700/50 rounded-xl border border-neutral-600 overflow-hidden flex flex-col">
        {/* Form Content */}
        <div className="flex-1 overflow-y-auto p-5">
          <div className="flex flex-col gap-5">
            {/* Section 1: Basic Information */}
            <div>
              <SectionHeader
                isRTL={isRTL}
                number={1}
                title={t("manualDiscovery.steps.basicInfo")}
              />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <InputField
                  label={t("manualDiscovery.form.cameraName")}
                  value={cameraName}
                  onChange={(e) => setCameraName(e.target.value)}
                  onBlur={(e) => handleBlur("cameraName", e)}
                  placeholder="Front Door Camera"
                  error={errors.cameraName}
                  required
                />
                <SelectField
                  label={t("manualDiscovery.form.category")}
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  onBlur={(e) => handleBlur("category", e)}
                  options={categoryOptions}
                  placeholderOption={t("manualDiscovery.form.selectCategory")}
                  error={errors.category}
                  required
                  isRTL={isRTL}
                />
                <SelectField
                  label={t("manualDiscovery.form.brand")}
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  onBlur={(e) => handleBlur("brand", e)}
                  options={brandOptions}
                  placeholderOption={t("manualDiscovery.form.selectBrand")}
                  error={errors.brand}
                  required
                  isRTL={isRTL}
                />
              </div>
            </div>
            {/* Divider */}
            <div className="border-t border-neutral-500"></div>
            {/* Section 2: Network Configuration */}
            <div>
              <SectionHeader
                isRTL={isRTL}
                number={2}
                title={t("manualDiscovery.steps.networkConfig")}
              />
              <div className={`flex flex-col md:flex-row gap-3`}>
                <InputField
                  label={t("manualDiscovery.form.ip")}
                  value={ipAddress}
                  onChange={(e) => setIpAddress(e.target.value)}
                  onBlur={(e) => handleBlur("ipAddress", e)}
                  placeholder="192.168.1.100"
                  error={errors.ipAddress}
                  required
                  className="font-mono"
                  containerClassName="md:flex-[2]"
                />
                <InputField
                  label={t("manualDiscovery.form.port")}
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  onBlur={(e) => handleBlur("port", e)}
                  placeholder="554"
                  error={errors.port}
                  className="font-mono"
                  containerClassName="md:flex-1"
                />
                <SelectField
                  label={t("manualDiscovery.form.protocol")}
                  value={protocol}
                  onChange={(e) => setProtocol(e.target.value)}
                  onBlur={(e) => handleBlur("protocol", e)}
                  options={protocolOptions}
                  placeholderOption={t("manualDiscovery.form.selectProtocol")}
                  error={errors.protocol}
                  required
                  isRTL={isRTL}
                  containerClassName="md:flex-[2]"
                />
                <ToggleButtons
                  label={t("manualDiscovery.form.transport")}
                  options={["TCP", "UDP"]}
                  value={transportProtocol}
                  onChange={(val) => setTransportProtocol(val as "TCP" | "UDP")}
                  containerClassName="md:flex-1"
                />
              </div>
            </div>
            {/* Divider */}
            <div className="border-t border-neutral-500"></div>
            {/* Section 3: Authentication */}
            <div>
              <SectionHeader
                isRTL={isRTL}
                number={3}
                title={t("manualDiscovery.steps.authentication")}
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <InputField
                  label={t("manualDiscovery.form.username")}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onBlur={(e) => handleBlur("username", e)}
                  placeholder="admin"
                  error={errors.username}
                />
                <PasswordField
                  label={t("manualDiscovery.form.password")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={(e) => handleBlur("password", e)}
                  placeholder="••••••••"
                  error={errors.password}
                  showPassword={showPassword}
                  setShowPassword={setShowPassword}
                  isRTL={isRTL}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer with Action Button */}
        <div className="bg-neutral-900/50 px-6 py-4 border-t border-neutral-700/50 flex items-center justify-between gap-4">
          {/* Info Section */}
          <div className="flex items-start gap-2 text-neutral-300 text-xs flex-1 min-w-0">
            <BiInfoCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="font-medium text-neutral-300 mb-1">
                {t("manualDiscovery.whenToUse.title")}
              </p>
              <ul className="space-y-0.5">
                {(
                  t("manualDiscovery.whenToUse.items", {
                    returnObjects: true,
                  }) as string[]
                )
                  .slice(0, 2)
                  .map((item, index) => (
                    <li
                      key={index}
                      className="text-xs text-neutral-400 truncate"
                    >
                      • {item}
                    </li>
                  ))}
              </ul>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleAdd}
            disabled={isSubmitting || hasErrors}
            className={`cursor-pointer bg-secondary-500 hover:bg-secondary-600 text-neutral-900 px-6 py-2.5 rounded-lg text-sm font-semibold transition-all hover:shadow-lg hover:shadow-secondary-500/25 hover:scale-105 active:scale-95 shrink-0 ${
              isSubmitting || hasErrors ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <div className="flex items-center justify-center gap-2 whitespace-nowrap">
              <BiPlus className="w-4 h-4" />
              {isSubmitting
                ? t("manualDiscovery.action.submitting")
                : t("manualDiscovery.action.add")}
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ManualDiscovery;
