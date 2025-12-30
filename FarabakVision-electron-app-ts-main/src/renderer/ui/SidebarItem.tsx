import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { createPortal } from "react-dom";
import { useState, useRef, Ref } from "react";
import { IconType } from "react-icons";

type Props = {
  id: string | number;
  icon: IconType;
  name: string;
  route?: string;
  onClick?: () => void;
  isActive?: boolean;
};

const SidebarItem = ({
  id,
  icon: Icon,
  name,
  route,
  onClick,
  isActive = false,
}: Props) => {
  const { t, i18n } = useTranslation("sidebar");
  const isRTL = i18n.dir() === "rtl";
  const [isHovered, setIsHovered] = useState(false);
  const ref = useRef<HTMLAnchorElement | HTMLButtonElement>(null);
  const viewportWidth = document.documentElement.clientWidth;

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
  };

  const commonProps = {
    className: `
      relative flex items-center justify-center
      w-12 h-12 rounded-3xl 
      transition-all duration-200 ease-out
      hover:bg-primary-700
      ${
        isActive
          ? "bg-primary-600 rounded-2xl"
          : "bg-neutral-700 hover:rounded-2xl"
      }
      group
    `,
    onMouseEnter: handleMouseEnter,
    onMouseLeave: handleMouseLeave,
  };

  const content = (
    <>
      <div className="text-neutral-50 transition-all">
        <Icon size={24} />
      </div>

      {/* Active indicator pill */}
      {isActive && (
        <div
          className={`absolute ${isRTL ? "-right-3" : "-left-3"} top-1/2 -translate-y-1/2 w-1 h-10 bg-neutral-50 ${isRTL ? "rounded-l-full" : "rounded-r-full"} transition-all`}
        />
      )}

      {/* Hover indicator pill */}
      {!isActive && isHovered && (
        <div
          className={`absolute ${isRTL ? "-right-3" : "-left-3"} top-1/2 -translate-y-1/2 w-1 h-5 bg-neutral-50 ${isRTL ? "rounded-l-full" : "rounded-r-full"} transition-all`}
        />
      )}
    </>
  );

  return (
    <div key={id} className="relative flex items-center">
      {route ? (
        <Link ref={ref as Ref<HTMLAnchorElement>} to={route} {...commonProps}>
          {content}
        </Link>
      ) : (
        <button
          ref={ref as Ref<HTMLButtonElement>}
          type="button"
          onClick={onClick}
          {...commonProps}
        >
          {content}
        </button>
      )}

      {isHovered &&
        ref.current &&
        createPortal(
          <div
            className={`bg-primary-600 text-white px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap z-2 shadow-lg`}
            style={{
              position: "absolute",
              top: `${ref.current.getBoundingClientRect().top + ref.current.getBoundingClientRect().height / 2}px`,
              transform: "translateY(-50%)",
              ...(isRTL
                ? {
                    right: `${viewportWidth - (ref.current.getBoundingClientRect().left + ref.current.getBoundingClientRect().width - 75)}px`,
                    left: "auto",
                  }
                : {
                    left: `${ref.current.getBoundingClientRect().left + 75}px`,
                    right: "auto",
                  }),
            }}
          >
            {t(`sidebar.${name}`)}
            <div
              className={`absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-primary-600 rotate-45 ${
                isRTL ? "right-0 translate-x-1" : "left-0 -translate-x-1"
              }`}
            />
          </div>,
          document.body
        )}
    </div>
  );
};

export default SidebarItem;
