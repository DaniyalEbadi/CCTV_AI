import { ReactNode } from "react";

const DashboardCard = ({
  children,
  extraclass,
}: {
  children: ReactNode;
  extraclass?: string;
}) => {
  return (
    <div
      className={`group relative bg-linear-to-br from-neutral-800 to-neutral-900 p-6 rounded-2xl
        transition-all duration-500 ease-out
        hover:shadow-[0_20px_60px_-15px] hover:shadow-primary-500/40
        border border-neutral-50/20 hover:border-primary-500
        before:absolute before:inset-0 before:rounded-2xl before:p-0.5
        before:bg-linear-to-br before:from-primary-300 before:to-primary-500
        before:opacity-0 hover:before:opacity-100
        before:transition-opacity before:duration-500 before:-z-1
        after:absolute after:inset-0.5 after:rounded-2xl after:bg-linear-to-br after:from-neutral-800 after:to-neutral-900 after:-z-1
        overflow-hidden h-full
        ${extraclass}`}
    >
      {/* Multiple radial glows for better coverage on large cards */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/15 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 hover:animate-pulse" />
      <div className="absolute top-1/2 right-1/4 w-80 h-80 bg-primary-400/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 delay-100 hover:animate-pulse" />
      <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl opacity-0 group-hover:opacity-80 transition-opacity duration-700 delay-200 hover:animate-pulse" />

      {/* Full width gradient overlay that breathes */}
      <div className="absolute inset-0 bg-linear-to-br from-primary-500/0 to-primary-500/0 group-hover:from-primary-500/5 group-hover:to-primary-600/5 transition-all duration-700 animate-pulse" />

      {/* Corner accents on all four corners for balance */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-linear-to-br from-primary-500/40 to-transparent rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-linear-to-tr from-primary-500/30 to-transparent rounded-tr-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl delay-150" />

      {/* Sharp corner highlights */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-linear-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xs" />
      <div className="absolute bottom-0 left-0 w-24 h-24 bg-linear-to-tr from-white/15 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100 blur-xs" />

      {/* Content */}
      <div className="relative z-1 h-full">{children}</div>

      {/* Subtle grain texture */}
      <div className="absolute inset-0 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity duration-300 pointer-events-none mix-blend-overlay">
        <svg className="w-full h-full">
          <filter id="noise">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.8"
              numOctaves="4"
            />
          </filter>
          <rect width="100%" height="100%" filter="url(#noise)" />
        </svg>
      </div>
    </div>
  );
};
export default DashboardCard;
