import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import NavbarAuth from "./NavbarAuth";
import FooterAuth from "./FooterAuth";

const LayoutAuth = () => {
  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex flex-col flex-1">
        <NavbarAuth />
        <main className="flex-1 p-4 overflow-y-auto ">
          <Outlet />
        </main>

        <FooterAuth />
      </div>
    </div>
  );
};

export default LayoutAuth;
