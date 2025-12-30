import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BiNetworkChart, BiSearch, BiShield } from "react-icons/bi";
import { CgLock } from "react-icons/cg";
import { TiWiFi } from "react-icons/ti";

const AutoDiscovery = () => {
  const [scanning, setScanning] = useState(false);
  const { t } = useTranslation("discoveryPage");

  return (
    <div className="w-full flex flex-col gap-8 animate-fade-in">
      {/* Header Card */}
      <div className="bg-linear-to-br from-primary-500/30 to-primary-600/30 border border-primary-600 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary-500/20 rounded-xl">
            <TiWiFi className="w-6 h-6 text-primary-300" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-neutral-50 mb-2">
              {t("autoDiscovery.header.title")}
            </h2>
            <p className="text-neutral-300 text-sm leading-relaxed">
              {t("autoDiscovery.header.description")}
            </p>
          </div>
        </div>
      </div>

      {/* How It Works & Benefits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* How It Works */}
        <div className="bg-neutral-800 rounded-2xl p-6 border border-neutral-500">
          <h3 className="text-lg font-semibold text-neutral-50 mb-4 flex items-center gap-2">
            <BiNetworkChart className="w-6 h-6 text-primary-500" />
            {t("autoDiscovery.howItWorks.title")}
          </h3>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {[
              { key: "scan", index: 1 },
              { key: "detect", index: 2 },
              { key: "connect", index: 3 },
            ].map(({ key, index }) => (
              <div key={key} className="flex items-start gap-3">
                <div className="shrink-0 w-8 h-8 bg-primary-500/20 rounded-full flex items-center justify-center text-primary-200 font-semibold text-sm">
                  {index}
                </div>
                <div>
                  <p className="text-white font-medium text-sm mb-1">
                    {t(`autoDiscovery.steps.${key}.title`)}
                  </p>
                  <p className="text-neutral-400 text-xs">
                    {t(`autoDiscovery.steps.${key}.description`)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Benefits */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="bg-neutral-800 rounded-xl p-6 border border-neutral-500">
            <div className="flex items-center gap-3 mb-4">
              <CgLock className="w-5 h-5 text-green-400" />
              <h4 className="text-white font-medium">
                {t("autoDiscovery.benefits.quick.title")}
              </h4>
            </div>
            <p className="text-neutral-400 text-sm">
              {t("autoDiscovery.benefits.quick.description")}
            </p>
          </div>

          <div className="bg-neutral-800 rounded-xl p-6 border border-neutral-500">
            <div className="flex items-center gap-3 mb-4">
              <BiShield className="w-5 h-5 text-purple-400" />
              <h4 className="text-white font-medium">
                {t("autoDiscovery.benefits.reliable.title")}
              </h4>
            </div>
            <p className="text-neutral-400 text-sm">
              {t("autoDiscovery.benefits.reliable.description")}
            </p>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="bg-neutral-800 rounded-2xl p-6 border border-neutral-500">
        <button
          onClick={() => setScanning(!scanning)}
          className={`w-full py-4 rounded-xl font-medium transition-all ${
            scanning
              ? "bg-neutral-500 hover:bg-neutral-600 text-white"
              : "bg-primary-600 hover:bg-primary-700 text-white"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            {scanning ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t("autoDiscovery.action.scanning")}
              </>
            ) : (
              <>
                <BiSearch className="w-5 h-5" />
                {t("autoDiscovery.action.start")}
              </>
            )}
          </div>
        </button>

        {scanning && (
          <p className="text-center text-neutral-400 text-sm mt-4">
            {t("autoDiscovery.action.hint")}
          </p>
        )}
      </div>
    </div>
  );
};

export default AutoDiscovery;
