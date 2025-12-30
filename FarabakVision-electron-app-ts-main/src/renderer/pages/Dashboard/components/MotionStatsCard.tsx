import { useEffect, useState } from "react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import DashboardCard from "./DashboardCard";
import type { IMotionDataPoint, IMotionStats } from "@/types/electronAPI";
import { useTranslation } from "react-i18next";

/**
 * Props for the custom tooltip component
 */
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: IMotionDataPoint;
  }>;
}

/**
 * Custom Tooltip for the chart
 */
const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  const { t } = useTranslation("dashboard");

  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-xl">
        <p className="text-white text-sm font-medium">
          {payload[0].payload.time}
        </p>
        <p className="text-cyan-400 text-sm">
          {t("motionStatsCard.motionEvents")}:{" "}
          <span className="font-semibold">{payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

/**
 * MotionStatsCard Component
 * Displays motion detection statistics with a Recharts line chart
 * Shows motion events over time with peak and total counts
 * Data is fetched via IPC from the main process
 *
 * @component
 * @returns React component displaying motion statistics with chart
 */
const MotionStatsCard: React.FC = () => {
  const { t, i18n } = useTranslation("dashboard");
  const isRTL = i18n.dir() === "rtl";

  // State to hold motion statistics data
  const [motionStats, setMotionStats] = useState<IMotionStats | null>(null);
  // State to manage loading state
  const [isLoading, setIsLoading] = useState(true);
  // State to manage error state
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch motion statistics on component mount
   * Uses IPC to get motion detection data from main process
   */
  useEffect(() => {
    const fetchMotionStats = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // Call the dashboard bridge to get motion statistics
        const data = await window.electronAPI.dashboard.getMotionStats();
        setMotionStats(data);
      } catch (err) {
        // Handle any errors that occur during data fetching
        setError(t("motionStatsCard.fetchFailed"));
        console.error("Error fetching motion stats:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMotionStats();
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("motionStatsCard.loading")}</p>
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
            {t("motionStatsCard.errorPrefix")} {error}
          </p>
        </div>
      </DashboardCard>
    );
  }

  // Render empty state
  if (!motionStats || motionStats.dataPoints.length === 0) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("motionStatsCard.empty")}</p>
        </div>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-6">
          <h3 className="text-base font-semibold text-white/90">
            {t("motionStatsCard.title")}
          </h3>
        </div>

        {/* Chart Container */}
        <div
          className="flex-1 bg-gray-800/30 rounded-lg p-4"
          style={{ minHeight: "300px" }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={motionStats.dataPoints}
              margin={{
                top: 20,
                right: isRTL ? 0 : 40,
                left: isRTL ? 40 : 0,
                bottom: 0,
              }}
            >
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="25%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="5 5"
                stroke="#4b5563"
                opacity={0.3}
              />
              <XAxis
                dataKey="time"
                stroke="#9ca3af"
                style={{ fontSize: "12px" }}
                reversed={isRTL}
              />
              <YAxis
                stroke="#9ca3af"
                style={{ fontSize: "12px" }}
                orientation={isRTL ? "right" : "left"}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#06b6d4"
                strokeWidth={2}
                fill="url(#colorCount)"
                dot={{ fill: "#06b6d4", r: 5 }}
                activeDot={{ r: 6 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Statistics Footer */}
        <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-600">
          {/* Total Events */}
          <div className="text-center flex-1">
            <p className="text-xs text-gray-400 mb-1">
              {t("motionStatsCard.totalEvents")}
            </p>
            <p className="text-lg font-semibold text-white">
              {motionStats.totalEvents}
            </p>
          </div>

          {/* Peak Count */}
          <div className="text-center flex-1 border-l border-r border-gray-600">
            <p className="text-xs text-gray-400 mb-1">
              {t("motionStatsCard.peakEvents")}
            </p>
            <p className="text-lg font-semibold text-cyan-400">
              {motionStats.peakCount}
            </p>
          </div>

          {/* Time Range */}
          <div className="text-center flex-1">
            <p className="text-xs text-gray-400 mb-1">
              {t("motionStatsCard.timeRange")}
            </p>
            <p className="text-sm font-medium text-white">
              {t("motionStatsCard.timeRangeValue")}
            </p>
          </div>
        </div>
      </div>
    </DashboardCard>
  );
};

export default MotionStatsCard;
