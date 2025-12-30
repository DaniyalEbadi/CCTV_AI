import { FaHome } from "react-icons/fa";
import CameraStreamsPage from "../pages/Camera-Streams/page";
import DashboardPage from "../pages/Dashboard/page";
import DiscoveryPage from "../pages/Discovery/page";
import HardwareSettingsPage from "../pages/Hardware-Settings/page";
import InfoPage from "../pages/Info/page";
import SettingsPage from "../pages/Settings/page";
import SubscriptionsPage from "../pages/Subscriptions/page";
import UserHubPage from "../pages/UserHub/page";
import { HiMiniViewfinderCircle } from "react-icons/hi2";
import { BiSolidCctv } from "react-icons/bi";
import { IoHardwareChip } from "react-icons/io5";
import { AiFillSetting } from "react-icons/ai";
import { RiUserSettingsFill } from "react-icons/ri";
import { PiInfoFill } from "react-icons/pi";
import { MdSubscriptions } from "react-icons/md";

export const pagesList = [
  {
    id: 1,
    name: "Dashboard",
    route: "/",
    component: DashboardPage,
    icon: FaHome,
  },
  {
    id: 2,
    name: "Discovery",
    route: "/discovery",
    component: DiscoveryPage,
    icon: HiMiniViewfinderCircle,
  },
  {
    id: 3,
    name: "Camera-Streams",
    route: "/camera-streams",
    component: CameraStreamsPage,
    icon: BiSolidCctv,
  },
  {
    id: 4,
    name: "Subscriptions",
    route: "/subscriptions",
    component: SubscriptionsPage,
    icon: MdSubscriptions,
  },
  {
    id: 5,
    name: "Hardware-Settings",
    route: "/hardware-settings",
    component: HardwareSettingsPage,
    icon: IoHardwareChip,
  },
  {
    id: 6,
    name: "Settings",
    route: "/settings",
    component: SettingsPage,
    icon: AiFillSetting,
  },
  {
    id: 7,
    name: "User-Hub",
    route: "/user-hub",
    component: UserHubPage,
    icon: RiUserSettingsFill,
  },
  {
    id: 8,
    name: "Info",
    route: "/Info",
    component: InfoPage,
    icon: PiInfoFill,
  },
];
