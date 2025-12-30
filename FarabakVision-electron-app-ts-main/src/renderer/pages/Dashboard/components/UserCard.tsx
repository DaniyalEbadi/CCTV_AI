/**
 * UserCard Component
 * Displays user and system information on the dashboard
 * Shows: Username, OS, MAC address, and connection status
 * Data is fetched via IPC from the main process (mock data)
 */

import { useEffect, useState } from "react";
import DashboardCard from "./DashboardCard";
import type { IUserData } from "@/types/electronAPI";
import { useTranslation } from "react-i18next";

/**
 * UserCard Component
 * Displays system admin information and connection status
 * Fetches user data via IPC on component mount
 *
 * @component
 * @returns React component displaying user and system information
 */
const UserCard: React.FC = () => {
  const { t } = useTranslation("dashboard");

  // State to hold user data
  const [userData, setUserData] = useState<IUserData | null>(null);
  // State to manage loading state
  const [isLoading, setIsLoading] = useState(true);
  // State to manage error state
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch user data on component mount
   * Uses IPC to get user information from main process
   */
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // Call the dashboard bridge to get user data
        const data = await window.electronAPI.dashboard.getUserData();
        setUserData(data);
      } catch (err) {
        // Handle any errors that occur during data fetching
        const errorMessage = t("userCard.fetchFailed");
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("userCard.loadingData")}</p>
        </div>
      </DashboardCard>
    );
  }

  // Render error state
  if (error) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-red-400">{error}</p>
        </div>
      </DashboardCard>
    );
  }

  // Render empty state (shouldn't happen but handle it)
  if (!userData) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("userCard.noData")}</p>
        </div>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <div className="flex flex-col h-full justify-between">
        {/* Header - Title */}
        <div className="mb-4">
          <h3 className="text-base font-semibold text-white/90">
            {userData.username}
          </h3>
        </div>

        {/* Content - User Info */}
        <div className="space-y-2 text-xs text-gray-300">
          {/* Connection Status */}
          <div className="flex items-center justify-between">
            <span className="text-gray-500">
              {t("userCard.connectionStatus")}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-white">{userData.connectionStatus}</span>
              {/* Status Indicator Dot */}
              <div
                className={`w-2 h-2 rounded-full ${
                  userData.connectionStatus === "connected"
                    ? "bg-green-500 animate-pulse"
                    : "bg-red-500"
                }`}
              />
            </div>
          </div>

          {/* Connected Since */}
          <div className="flex items-center justify-between">
            <span className="text-gray-500">
              {t("userCard.connectedSince")}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-white" dir="ltr">
                {userData.connectedSince}
              </span>
            </div>
          </div>

          {/* OS Information */}
          <div className="flex items-center justify-between">
            <span className="text-gray-500">{t("userCard.osInfo")}</span>
            <span className="text-white">{userData.osName}</span>
          </div>

          {/* MAC Address */}
          <div className="flex items-center justify-between">
            <span className="text-gray-500">{t("userCard.macAddress")}</span>
            <span className="text-white text-xs font-mono" dir="ltr">
              {userData.macAddress}
            </span>
          </div>
        </div>
      </div>
    </DashboardCard>
  );
};

export default UserCard;
