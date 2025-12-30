import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { FaRegKeyboard } from "react-icons/fa";
import { RiRadarLine } from "react-icons/ri";
import AutoDiscovery from "./AutoDiscovery";
import ManualDiscovery from "./manualDiscovery/ManualDiscovery";

type DiscoveryMode = "auto" | "manual";

const ModeSelector = () => {
  const [mode, setMode] = useState<DiscoveryMode>("auto");

  const containerRef = useRef<HTMLDivElement>(null);
  const autoRef = useRef<HTMLButtonElement>(null);
  const manualRef = useRef<HTMLButtonElement>(null);

  const [indicatorStyle, setIndicatorStyle] = useState({
    width: 0,
    left: 0,
  });

  const { t, i18n } = useTranslation("discoveryPage");
  const isRTL = i18n.dir() === "rtl";

  useEffect(() => {
    const updateIndicator = () => {
      const activeRef = mode === "auto" ? autoRef : manualRef;
      if (!activeRef.current || !containerRef.current) return;

      const { offsetWidth, offsetLeft } = activeRef.current;

      setIndicatorStyle({
        width: offsetWidth,
        left: offsetLeft,
      });
    };

    updateIndicator();

    const resizeObserver = new ResizeObserver(() => {
      updateIndicator();
    });

    if (autoRef.current) resizeObserver.observe(autoRef.current);
    if (manualRef.current) resizeObserver.observe(manualRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [mode, isRTL]);

  return (
    <>
      <div
        ref={containerRef}
        className="relative bg-neutral-700 rounded-full flex items-center w-fit mx-auto p-1 mb-8"
      >
        <div
          className="absolute top-1 bottom-1 rounded-full bg-neutral-950 transition-all duration-300 ease-out"
          style={{
            width: indicatorStyle.width,
            left: indicatorStyle.left,
          }}
        />

        <button
          ref={autoRef}
          onClick={() => setMode("auto")}
          className={`cursor-pointer relative z-10 flex items-center gap-2 px-5 py-2 rounded-full font-medium transition-colors ${
            mode === "auto" ? "text-white" : "text-neutral-400 hover:text-white"
          }`}
        >
          <RiRadarLine className="w-4 h-4" />
          {t("modeSelector.autoDiscovery")}
        </button>

        <button
          ref={manualRef}
          onClick={() => setMode("manual")}
          className={`cursor-pointer relative z-10 flex items-center gap-2 px-5 py-2 rounded-full font-medium transition-colors ${
            mode === "manual"
              ? "text-white"
              : "text-neutral-400 hover:text-white"
          }`}
        >
          <FaRegKeyboard className="w-4 h-4" />
          {t("modeSelector.manualDiscovery")}
        </button>
      </div>

      <div className="flex flex-1 w-full">
        {mode === "auto" ? <AutoDiscovery /> : <ManualDiscovery />}
      </div>
    </>
  );
};
export default ModeSelector;
