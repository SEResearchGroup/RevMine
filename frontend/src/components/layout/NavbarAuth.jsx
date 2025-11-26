import React from 'react';
import { Search, Plus, Mail, Bell } from 'lucide-react';

const NavbarAuth = () => {
  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 ">
      <div className="w-48"></div>      
      <div className="flex-1 max-w-2xl mx-auto">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-blue-500 w-5 h-5" />
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-10 pr-4 py-2 border-2 border-blue-500 rounded-lg focus:outline-none focus:border-blue-600"
          />
        </div>
      </div>
      
      {/* Right Section */}
      <div className="flex items-center gap-4 w-48 justify-end">
        <button className="p-2 hover:bg-gray-100 rounded-lg transition">
          <Plus className="w-5 h-5 text-blue-500" />
        </button>
        <button className="p-2 hover:bg-gray-100 rounded-lg transition">
          <Mail className="w-5 h-5 text-blue-500" />
        </button>
        <button className="p-2 hover:bg-gray-100 rounded-lg transition">
          <Bell className="w-5 h-5 text-blue-500" />
        </button>
        
        {/* Profile Section */}
        <div className="flex items-center gap-3 ml-2">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold">
            JD
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold text-gray-800">John Doe</span>
            <span className="text-xs text-gray-500">john@example.com</span>
            <span className="text-xs text-gray-400">Business Owner</span>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default NavbarAuth;