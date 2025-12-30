import { useState } from "react";
import SidebarItem from "./SidebarItem";
import { BiLogIn, BiLogOut } from "react-icons/bi";

const UserSidebarItem = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleClick = () => {
    setIsLoggedIn((prev) => !prev);
    // Dummy logic: In a real app, integrate with auth provider
  };

  return (
    <SidebarItem
      id="user"
      icon={isLoggedIn ? BiLogOut : BiLogIn}
      name={isLoggedIn ? "Logout" : "Login"}
      onClick={handleClick}
    />
  );
};

export default UserSidebarItem;
