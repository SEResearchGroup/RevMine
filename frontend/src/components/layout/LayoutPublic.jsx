import { Outlet } from "react-router-dom";
import NavbarPublic from "./NavbarPublic";
import FooterPublic from "./FooterPublic";

const LayoutPublic = () => {
  return (
    <div className="app-public-layout">
      <NavbarPublic />

      <main className="p-4">
        <Outlet />
      </main>

      <FooterPublic />
    </div>
  );
};

export default LayoutPublic;
