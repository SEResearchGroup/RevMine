import React, { useState, useEffect, useRef } from "react";
import { Search, Plus, Mail, User, Settings, LogOut } from "lucide-react";
import { authService } from "../../services/api";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import NotificationDropdown from "../ui/NotificationDropdown";

const NavbarAuth = () => {
  const [userInformation, setUserInformation] = useState({});
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await authService.getUserInfo();
        setUserInformation(response.data);
      } catch (error) {
        console.error("Error fetching user data:", error);
      }
    };

    fetchUserData();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="flex items-center justify-between px-3 sm:px-6 py-3 bg-white border-b border-gray-200">
      {/* Search - Hidden on small screens */}
      <div className="hidden md:flex flex-1 max-w-xl mx-auto">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-blue-500 w-5 h-5" />
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-10 pr-4 py-2 border-2 border-blue-500 rounded-lg focus:outline-none focus:border-blue-600"
          />
        </div>
      </div>

      {/* Mobile Search Icon */}
      <button className="md:hidden p-2 hover:bg-gray-100 rounded-lg transition">
        <Search className="w-5 h-5 text-blue-500" />
      </button>

      {/* Right side actions */}
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Action buttons - Some hidden on mobile */}
        <button className="hidden sm:block p-2 hover:bg-gray-100 rounded-lg transition">
          <Plus className="w-5 h-5 text-blue-500" />
        </button>
        <button className="hidden lg:block p-2 hover:bg-gray-100 rounded-lg transition">
          <Mail className="w-5 h-5 text-blue-500" />
        </button>
        <NotificationDropdown />

        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <div
            className="flex items-center gap-2 sm:gap-3 ml-2 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-linear-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-sm sm:text-base">
              {userInformation.first_name?.[0]}
              {userInformation.last_name?.[0]}
            </div>
            {/* User info - Hidden on small screens */}
            <div className="hidden lg:flex flex-col">
              <span
                className="text-sm font-bold text-gray-800 whitespace-nowrap max-w-[120px] overflow-hidden text-ellipsis"
                title={`${userInformation.first_name} ${userInformation.last_name}`}
              >
                {userInformation.first_name}{" "}
                {userInformation.last_name?.length > 8
                  ? userInformation.last_name.slice(0, 6) + "..."
                  : userInformation.last_name}
              </span>
              <span className="text-xs text-gray-500">
                {userInformation.email}
              </span>
            </div>
          </div>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-linear-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-lg">
                    {userInformation.first_name?.[0]}
                    {userInformation.last_name?.[0]}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">
                      {userInformation.first_name} {userInformation.last_name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {userInformation.email}
                    </p>
                    {userInformation.position && (
                      <p className="text-xs text-gray-400 mt-1">
                        {userInformation.position}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="py-2">
                <button
                  onClick={() => {
                    navigate("/profile");
                    setIsDropdownOpen(false);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition text-left cursor-pointer"
                >
                  <User className="w-5 h-5 text-gray-600" />
                  <span className="text-sm text-gray-700 font-medium">
                    My Profile
                  </span>
                </button>

                <button
                  onClick={() => {
                    navigate("/settings");
                    setIsDropdownOpen(false);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition text-left cursor-pointer"
                >
                  <Settings className="w-5 h-5 text-gray-600" />
                  <span className="text-sm text-gray-700 font-medium">
                    Settings
                  </span>
                </button>
              </div>

              <div className="border-t border-gray-200 py-2">
                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-red-50 transition text-left cursor-pointer"
                >
                  <LogOut className="w-5 h-5 text-red-600" />
                  <span className="text-sm text-red-600 font-medium">
                    Sign out
                  </span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default NavbarAuth;
