import { useEffect, useState } from "react";
import DashboardCard from "./DashboardCard";
import type { ICameraBrand } from "@/types/electronAPI";
import { useTranslation } from "react-i18next";
import PieChartComponent from "@/renderer/components/PieChartComponent";

const CameraBrandsCard: React.FC = () => {
  // State to hold camera brands data
  const [cameraBrands, setCameraBrands] = useState<ICameraBrand[]>([]);
  // State to manage loading state
  const [isLoading, setIsLoading] = useState(true);
  // State to manage error state
  const [error, setError] = useState<string | null>(null);

  const { t } = useTranslation("dashboard");

  useEffect(() => {
    const fetchCameraBrands = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // Call the dashboard bridge to get complete dashboard data
        // We extract just the camera brands from the response
        const data = await window.electronAPI.dashboard.getDashboardData();
        setCameraBrands(data.cameraBrands);
      } catch (err) {
        setError(t("cameraBrandsCard.fetchFailed"));
        console.error("Error fetching camera brands:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCameraBrands();
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("cameraBrandsCard.loading")}</p>
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
            {t("cameraBrandsCard.errorPrefix")} {error}
          </p>
        </div>
      </DashboardCard>
    );
  }

  // Render empty state
  if (cameraBrands.length === 0) {
    return (
      <DashboardCard>
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">{t("cameraBrandsCard.empty")}</p>
        </div>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <div className="flex flex-col h-full justify-between gap-5">
        {/* Header - Title */}
        <h3 className="text-base font-semibold text-white/90">
          {t("cameraBrandsCard.title")}
        </h3>

        <div className="flex justify-center">
          <PieChartComponent data={cameraBrands} dataKey="count" />
        </div>

        {/* Summary */}
        <div className="space-y-3 pt-4 border-t border-gray-600 text-sm text-gray-400">
          <p>
            {t("cameraBrandsCard.totalBrands")}{" "}
            <span className="text-white font-medium">
              {cameraBrands.length}
            </span>
          </p>
          <p className="font-medium">
            {t("cameraBrandsCard.totalCameras")}{" "}
            <span className="text-white font-medium">
              {cameraBrands.reduce((sum, brand) => sum + brand.value, 0)}
            </span>
          </p>
        </div>
      </div>
    </DashboardCard>
  );
};

export default CameraBrandsCard;
