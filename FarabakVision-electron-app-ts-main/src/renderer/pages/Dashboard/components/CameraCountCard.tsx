/**
 * CameraCountCard Component
 * Displays camera connection status with dynamic categories from IPC
 * Data is fetched via IPC from the main process
 */

import { useEffect, useState } from "react";
import DashboardCard from "./DashboardCard";
import type { ICameraStatus } from "@/types/electronAPI";
import { useTranslation } from "react-i18next";

import PieChartComponent from "@/renderer/components/PieChartComponent";

/**
 * CameraCountCard Component
 * Shows status indicators for different camera states
 * Fetches camera status via IPC on mount
 *
 * @component
 * @returns React component displaying camera status breakdown
 */
const CameraCountCard: React.FC = () => {
  // State to hold camera status data as an array
  const [cameraStatus, setCameraStatus] = useState<ICameraStatus[]>([]);
  // State to manage loading state
  const [isLoading, setIsLoading] = useState(true);
  // State to manage error state
  const [error, setError] = useState<string | null>(null);

  const { t } = useTranslation("dashboard");

  /**
   * Fetch camera status on component mount
   * Uses IPC to get camera connection information from main process
   */
  useEffect(() => {
    const fetchCameraStatus = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // Call the dashboard bridge to get camera status
        const data = await window.electronAPI.dashboard.getCameraStatus();
        setCameraStatus(data);
      } catch (err) {
        // Handle any errors that occur during data fetching
        const errorMessage = t("cameraCountCard.fetchFailed");
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCameraStatus();
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("cameraCountCard.loadingData")}</p>
        </div>
      </DashboardCard>
    );
  }

  // Render error state
  if (error) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-red-400">{t("cameraCountCard.fetchFailed")}</p>
        </div>
      </DashboardCard>
    );
  }

  // Render empty state
  if (!cameraStatus || cameraStatus.length === 0) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("cameraCountCard.noData")}</p>
        </div>
      </DashboardCard>
    );
  }

  // Transform data for pie chart
  const chartData = cameraStatus.map((status) => ({
    name: status.name,
    value: status.amount,
    fill: status.color,
  }));

  return (
    <DashboardCard>
      <div className="flex flex-col h-full justify-between gap-5">
        {/* Header - Title */}
        <h3 className="text-base font-semibold text-white/90">
          {t("cameraCountCard.title")}
        </h3>

        <div className="flex justify-center">
          <PieChartComponent data={chartData} />
        </div>

        {/* Camera Status Items - Dynamically rendered from IPC data */}
        <div className="space-y-3 pt-4 border-t border-gray-600">
          {cameraStatus.map((status) => (
            <div
              key={status.name}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-gray-400">
                {t(`cameraCountCard.${status.name}`)}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-white font-medium">{status.amount}</span>
                {/* Status Indicator with dynamic color */}
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: status.color }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardCard>
  );
};

export default CameraCountCard;
