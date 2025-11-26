import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import NavbarAuth from "./NavbarAuth";
import FooterAuth from "./FooterAuth";

const LayoutAuth = () => {
  return (
    <>
      <NavbarAuth />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </div>
      <FooterAuth />
    </>
  );
};

export default LayoutAuth;
