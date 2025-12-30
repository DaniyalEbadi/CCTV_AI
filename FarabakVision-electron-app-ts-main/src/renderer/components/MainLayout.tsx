import { Outlet } from "react-router-dom";
import DashboardSidebar from "../ui/DashboardSidebar";
import TitleBar from "./TitleBar";

const MainLayout = () => {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Custom Title Bar - Fixed height */}
      <TitleBar />

      {/* Main Content Area - Takes remaining height */}
      <div className="flex flex-1 gap-5 p-5 bg-background text-foreground overflow-hidden">
        <DashboardSidebar />
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
