import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  VscChromeMinimize,
  VscChromeMaximize,
  VscChromeRestore,
  VscClose,
} from "react-icons/vsc";
import { pagesList } from "../constants/pagesList";

const TitleBar: React.FC = () => {
  const { t, i18n } = useTranslation("sidebar");
  const isRTL = i18n.dir() === "rtl";

  const location = useLocation();
  const [isMaximized, setIsMaximized] = useState(false);
  const [currentPage, setCurrentPage] = useState<(typeof pagesList)[0] | null>(
    null
  );

  useEffect(() => {
    // Find current page based on route
    const page = pagesList.find((p) => p.route === location.pathname);
    setCurrentPage(page || pagesList[0]); // Default to Dashboard if not found
  }, [location.pathname]);

  useEffect(() => {
    // Get initial maximized state
    window.electronAPI.window.isMaximized().then(setIsMaximized);

    // Listen for maximize/unmaximize events
    window.electronAPI.window.onMaximized((maximized) => {
      setIsMaximized(maximized);
    });

    return () => {
      window.electronAPI.window.removeMaximizedListener();
    };
  }, []);

  const handleMinimize = () => {
    window.electronAPI.window.minimize();
  };

  const handleMaximize = () => {
    window.electronAPI.window.maximize();
  };

  const handleClose = () => {
    window.electronAPI.window.close();
  };

  const PageIcon = currentPage?.icon;

  return (
    <div
      className="flex items-center h-10 bg-[#1a1d1f] border-b border-[#2a2d2f] select-none relative"
      dir="ltr"
    >
      {/* Left spacer for balance (draggable) */}
      <div className="flex-1 h-full titlebar-drag-region" />

      {/* Center section - Page title and icon (draggable) */}
      <div
        dir={isRTL ? "rtl" : "ltr"}
        className="flex items-center justify-center gap-2 px-4 h-full titlebar-drag-region absolute left-1/2 -translate-x-1/2"
      >
        {PageIcon && <PageIcon className="w-4 h-4 text-gray-400 shrink-0" />}
        <span className="text-sm font-medium text-gray-200 whitespace-nowrap">
          {currentPage ? t(`sidebar.${currentPage.name}`) : ""}
        </span>
      </div>

      {/* Right section - Window controls (not draggable) */}
      <div className="flex h-full ml-auto">
        {/* Minimize button */}
        <button
          onClick={handleMinimize}
          className="w-9 h-full flex items-center justify-center hover:bg-[#2a2d2f] group [transition:none!important]"
          aria-label="Minimize"
          type="button"
        >
          <VscChromeMinimize className="w-4 h-4 text-gray-400 group-hover:text-gray-200 [transition:none!important]" />
        </button>

        {/* Maximize/Restore button */}
        <button
          onClick={handleMaximize}
          className="w-9 h-full flex items-center justify-center hover:bg-[#2a2d2f] group [transition:none!important]"
          aria-label={isMaximized ? "Restore" : "Maximize"}
          type="button"
        >
          {isMaximized ? (
            <VscChromeRestore className="w-4 h-4 text-gray-400 group-hover:text-gray-200 [transition:none!important]" />
          ) : (
            <VscChromeMaximize className="w-4 h-4 text-gray-400 group-hover:text-gray-200 [transition:none!important]" />
          )}
        </button>

        {/* Close button */}
        <button
          onClick={handleClose}
          className="w-9 h-full flex items-center justify-center hover:bg-red-600 group [transition:none!important]"
          aria-label="Close"
          type="button"
        >
          <VscClose className="w-5 h-5 text-gray-400 group-hover:text-white [transition:none!important]" />
        </button>
      </div>
    </div>
  );
};

export default TitleBar;
