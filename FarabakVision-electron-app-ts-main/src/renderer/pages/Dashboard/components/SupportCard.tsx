/**
 * SupportCard Component
 * Displays support information and links
 * Shows support status and provides access to support resources
 * This is a static card - no dynamic data fetching required
 */

/**
 * SupportCard Component
 * Shows support information with action button
 *
 * @component
 * @returns React component displaying support information
 */
import DashboardCard from "./DashboardCard";
import { useTranslation } from "react-i18next";

const SupportCard: React.FC = () => {
  const { t } = useTranslation("dashboard");

  /**
   * Handles support button click
   * In the future, this will open support resources or contact dialog
   */
  const handleSupportClick = () => {
    console.log("Support button clicked");
    // TODO: Implement support actions
    // Examples:
    // - Open support documentation
    // - Open contact support form
    // - Start live chat
  };

  return (
    <DashboardCard>
      <div className="flex flex-col h-full justify-between">
        {/* Header - Title */}
        <div className="mb-6">
          <h3 className="text-base font-semibold text-white/90">
            {t("supportCard.title")}
          </h3>
          <p className="text-xs text-gray-400 mt-2">
            {t("supportCard.subtitle")}
          </p>
        </div>

        {/* Support Status Information */}
        <div className="space-y-3 flex-1">
          {/* Support Status Indicator */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">
              {t("supportCard.supportStatusLabel")}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-green-400 font-medium">
                {t("supportCard.supportAvailable")}
              </span>
              {/* Status Indicator - Green dot */}
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            </div>
          </div>

          {/* Support Channel Info */}
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-2">
              {t("supportCard.channelsTitle")}
            </p>
            <div className="space-y-1 text-xs text-gray-300">
              <p>📧 {t("supportCard.email")}: support@farabakvision.com</p>
              <p>📞 {t("supportCard.phone")}: +98 21 xxxx xxxx</p>
              <p>
                💬 {t("supportCard.liveChat")}: {t("supportCard.liveChatTime")}
              </p>
            </div>
          </div>
        </div>

        {/* Support Button */}
        <button
          onClick={handleSupportClick}
          className="
            w-full mt-4 py-2 px-4 rounded-lg
            bg-linear-to-r from-primary-600 to-primary-500
            text-white text-sm font-medium
            hover:from-primary-500 hover:to-primary-400
            transition-all duration-300 ease-out
            hover:shadow-lg hover:shadow-primary-500/30
            border border-primary-400/30 hover:border-primary-400/50
            group relative overflow-hidden
          "
        >
          {/* Hover effect shine */}
          <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-lg" />

          <span className="relative z-10 text-center">
            {t("supportCard.button")}
          </span>
        </button>
      </div>
    </DashboardCard>
  );
};

export default SupportCard;
