import CameraBrandsCard from "./components/CameraBrandsCard";
import CameraCountCard from "./components/CameraCountCard";
import MotionStatsCard from "./components/MotionStatsCard";
import QuickActionsCard from "./components/QuickActionsCard";
import SupportCard from "./components/SupportCard";
import UserCard from "./components/UserCard";

const DashboardPage = () => {
  return (
    <div className="w-full h-full overflow-y-auto no-scrollbar flex flex-col gap-5">
      {/* First row Cards */}
      <div className="flex gap-5 flex-wrap lg:flex-nowrap flex-2/6">
        <div className="w-[calc(50%-0.625rem)] lg:w-auto lg:flex-1">
          <UserCard />
        </div>
        <div className="w-[calc(50%-0.625rem)] lg:w-auto lg:flex-1">
          <CameraCountCard />
        </div>
        <div className="w-[calc(50%-0.625rem)] lg:w-auto lg:flex-1">
          <CameraBrandsCard />
        </div>
        <div className="w-[calc(50%-0.625rem)] lg:w-auto lg:flex-1">
          <SupportCard />
        </div>
      </div>

      {/* Second row Card */}
      <div className="flex-3/6">
        <MotionStatsCard />
      </div>

      {/* Third Row Card */}
      <div className=" flex-1/6">
        <QuickActionsCard />
      </div>
    </div>
  );
};

export default DashboardPage;
