import React from "react";
import logo from "../../assets/images/logo_v1.png";

const NavbarPublic = () => {
  return (
    <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-start items-center h-16">
        <div className="flex items-center">
          <img src={logo} alt="RevMine Logo" className="h-10 w-auto" />
        </div>
      </div>
    </nav>
  );
};

export default NavbarPublic;
