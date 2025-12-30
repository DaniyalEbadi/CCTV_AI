// Reusable Section Header
const SectionHeader = ({
  number,
  title,
  isRTL,
}: {
  number: number;
  title: string;
  isRTL?: boolean;
}) => (
  <h3 className="text-base font-semibold text-neutral-300 uppercase tracking-wider mb-6 flex items-center gap-2">
    <span
      className={`w-5 h-5 rounded-full bg-secondary-500/20 text-secondary-400 flex items-center justify-center text-xs font-bold ${isRTL ? "pt-0.5" : ""}`}
    >
      {number}
    </span>
    {title}
  </h3>
);

export default SectionHeader;
