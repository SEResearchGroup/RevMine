import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import NavbarAuth from "./NavbarAuth";
import FooterAuth from "./FooterAuth";

const LayoutAuth = () => {
  return (
    <div className="app-auth-layout">
      <NavbarAuth />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </div>
      <FooterAuth />
    </div>
  );
};

export default LayoutAuth;
