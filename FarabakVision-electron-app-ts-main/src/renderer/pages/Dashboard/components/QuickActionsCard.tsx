/**
 * QuickActionsCard Component
 * Displays quick action buttons for common dashboard operations
 * Shows: Start/Stop Recording, View Streams, Export Video
 * Data is fetched via IPC from the main process
 */

import { useEffect, useState } from "react";
import DashboardCard from "./DashboardCard";
import type { IQuickAction } from "@/types/electronAPI";
import { useTranslation } from "react-i18next";

/**
 * QuickActionsCard Component
 * Shows action tiles for quick operations
 * Fetches quick actions via IPC on mount
 *
 * @component
 * @returns React component displaying quick action buttons
 */
const QuickActionsCard: React.FC = () => {
  const { t } = useTranslation("dashboard");

  // State to hold quick actions data
  const [quickActions, setQuickActions] = useState<IQuickAction[]>([]);
  // State to manage loading state
  const [isLoading, setIsLoading] = useState(true);
  // State to manage error state
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch quick actions on component mount
   * Uses IPC to get available actions from main process
   */
  useEffect(() => {
    const fetchQuickActions = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // TEMP: Replace with real IPC later
        const data = await window.electronAPI.dashboard.getDashboardData();
        setQuickActions(data.quickActions);
      } catch (err) {
        setError(t("quickActionsCard.fetchFailed"));
        console.error("Error fetching quick actions:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuickActions();
  }, [t]);

  /**
   * Handles action button clicks
   * In the future, this will dispatch actual actions
   *
   * @param action - The action identifier to perform
   */
  const handleAction = (action: string) => {
    console.log(`Action triggered: ${action}`);
    // TODO: Implement actual action handlers
    // Examples:
    // - startRecording: trigger camera recording
    // - stopRecording: stop all recordings
    // - viewStreams: navigate to streams page
    // - exportVideo: open export dialog
  };

  // Render loading state
  if (isLoading) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("quickActionsCard.loading")}</p>
        </div>
      </DashboardCard>
    );
  }

  // Render error state
  if (error) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-red-400">
            {t("quickActionsCard.errorPrefix")} {error}
          </p>
        </div>
      </DashboardCard>
    );
  }

  // Render empty state
  if (quickActions.length === 0) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("quickActionsCard.empty")}</p>
        </div>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <div className="flex flex-col h-full">
        {/* Header */}
        <h3 className="text-base font-semibold text-white/90 mb-6 text-right">
          {t("quickActionsCard.title")}
        </h3>

        {/* Action Grid */}
        {/* Creates a responsive grid with 4 equal columns */}
        <div className="flex flex-1 gap-4 justify-between">
          {quickActions.map((action: IQuickAction) => {
            const label = t(`quickActionsCard.actions.${action.id}`);

            return (
              <button
                key={action.id}
                onClick={() => handleAction(action.action)}
                className={`
                  flex flex-col flex-1 items-center justify-center p-4 rounded-lg cursor-pointer
                  bg-linear-to-br from-gray-700 to-gray-800
                  border border-gray-600 hover:border-primary-500
                  transition-all duration-300 ease-out
                  hover:shadow-lg hover:shadow-primary-500/20
                  hover:from-gray-600 hover:to-gray-700
                  group relative overflow-hidden
                  ${action.className || ""}
                `}
                title={label}
              >
                {/* Hover effect background */}
                <div className="absolute inset-0 bg-primary-500 opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-lg" />

                {/* Icon placeholder - circular icon area */}
                <div className="w-10 h-10 rounded-full bg-gray-600 group-hover:bg-primary-600 transition-colors duration-300 mb-2 flex items-center justify-center relative z-1">
                  {/* Icon character - can be replaced with actual icons */}
                  <span className="text-white text-lg font-bold">
                    {action.id.charAt(0).toUpperCase()}
                  </span>
                </div>

                {/* Action Label */}
                <span className="text-xs text-gray-300 group-hover:text-white transition-colors duration-300 text-center font-medium relative z-1">
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </DashboardCard>
  );
};

export default QuickActionsCard;
