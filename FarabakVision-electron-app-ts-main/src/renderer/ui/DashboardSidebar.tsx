import { pagesList } from "../constants/pagesList";
import { useLocation } from "react-router-dom";
import UserSidebarItem from "./UserSidebarItem";
import LanguageSidebarItem from "./LanguageSidebarItem";
import SidebarItem from "./SidebarItem";

const DashboardSidebar = () => {
  const location = useLocation();

  return (
    <div className="flex h-full rounded-xl bg-neutral-800 border border-neutral-50/20 w-[72px] flex-col items-center py-5 gap-4 no-scrollbar overflow-y-auto">
      {/* Page Items */}
      {pagesList.map((item) => (
        <SidebarItem
          key={item.id}
          id={item.id}
          icon={item.icon}
          name={item.name}
          route={item.route}
          isActive={location.pathname === item.route}
        />
      ))}

      {/* Subscriptions - Empty for now */}

      {/* Actions => Signup/Login/Logout | Change Language */}
      <div className="mt-auto flex flex-col items-center gap-4">
        <UserSidebarItem />
        <LanguageSidebarItem />
      </div>
    </div>
  );
};

export default DashboardSidebar;
