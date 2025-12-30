import { useTranslation } from "react-i18next";
import { createPortal } from "react-dom";
import { useState, useRef, useLayoutEffect, useEffect } from "react";
import { BiGlobe } from "react-icons/bi";

const LanguageSidebarItem = () => {
  const { t, i18n } = useTranslation("sidebar");
  const isRTL = i18n.dir() === "rtl";
  const [isHovered, setIsHovered] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuHeight, setMenuHeight] = useState(0);
  const [positionRect, setPositionRect] = useState<DOMRect | undefined>(
    undefined
  );

  useEffect(() => {
    const updateRect = () => {
      if (buttonRef.current) {
        setPositionRect(buttonRef.current.getBoundingClientRect());
      }
    };

    if (showMenu || isHovered) {
      updateRect();
      window.addEventListener("resize", updateRect);
      return () => window.removeEventListener("resize", updateRect);
    } else {
      setPositionRect(undefined); // Optional: Clear when not needed
    }
  }, [showMenu, isHovered]);

  const viewportWidth = document.documentElement.clientWidth;

  const languages = [
    { code: "en", labelKey: "en" },
    { code: "fa", labelKey: "fa" },
    { code: "ar", labelKey: "ar" },
  ];

  const changeLang = (newLang: string) => {
    i18n.changeLanguage(newLang);
    document.dir = newLang === "fa" || newLang === "ar" ? "rtl" : "ltr";
    window.electronAPI.setLanguage(newLang); // Persists
    setShowMenu(false);
  };

  useLayoutEffect(() => {
    if (showMenu && menuRef.current) {
      setMenuHeight(menuRef.current.offsetHeight);
    }
  }, [showMenu]);

  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setShowMenu(false);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [showMenu]);

  const rect = positionRect;

  const menuTop =
    menuHeight > 0 && rect
      ? rect.bottom - menuHeight
      : rect
        ? rect.top + rect.height / 2
        : 0;
  const menuTransform = menuHeight > 0 ? "none" : "translateY(-50%)";

  return (
    <div className="relative flex items-center">
      <button
        ref={buttonRef}
        type="button"
        className={`
          relative flex items-center justify-center cursor-pointer
          w-12 h-12 rounded-3xl 
          transition-all duration-200 ease-out
          hover:bg-primary-600
          bg-neutral-600 hover:rounded-2xl
          group
        `}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => setShowMenu(() => !showMenu)}
      >
        <div className="text-neutral-50 transition-all">
          <BiGlobe size={24} />
        </div>

        {/* Hover indicator pill */}
        {isHovered && (
          <div
            className={`absolute ${isRTL ? "-right-3" : "-left-3"} top-1/2 -translate-y-1/2 w-1 h-5 bg-neutral-50 ${isRTL ? "rounded-l-full" : "rounded-r-full"} transition-all`}
          />
        )}
      </button>

      {isHovered &&
        rect &&
        createPortal(
          <div
            className={`bg-primary-600 text-white px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap z-2 shadow-lg`}
            style={{
              position: "absolute",
              top: `${rect.top + rect.height / 2}px`,
              transform: "translateY(-50%)",
              ...(isRTL
                ? {
                    right: `${viewportWidth - (rect.left + rect.width - 75)}px`,
                    left: "auto",
                  }
                : {
                    left: `${rect.left + 75}px`,
                    right: "auto",
                  }),
            }}
          >
            {t("sidebar.Language")}
            <div
              className={`absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-primary-600 rotate-45 ${
                isRTL ? "right-0 translate-x-1" : "left-0 -translate-x-1"
              }`}
            />
          </div>,
          document.body
        )}

      {showMenu &&
        rect &&
        createPortal(
          <div
            ref={menuRef}
            className={`bg-primary-600 text-white p-2 rounded-md shadow-lg z-3 min-w-[120px]`}
            style={{
              position: "absolute",
              top: `${menuTop}px`,
              transform: menuTransform,
              ...(isRTL
                ? {
                    right: `${viewportWidth - (rect.left + rect.width - 75)}px`,
                    left: "auto",
                  }
                : {
                    left: `${rect.left + 75}px`,
                    right: "auto",
                  }),
            }}
          >
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => changeLang(lang.code)}
                className="block rounded-xl w-full px-4 py-2 hover:bg-primary-700 transition-colors cursor-pointer"
              >
                {t(`languages.${lang.labelKey}`)}
              </button>
            ))}
            <div
              className={`absolute bottom-[17px] -translate-y-1/2 w-2 h-2 bg-primary-600 rotate-45 ${
                isRTL ? "right-0 translate-x-1" : "left-0 -translate-x-1"
              }`}
            />
          </div>,
          document.body
        )}
    </div>
  );
};

export default LanguageSidebarItem;
