import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css";

export function Layout() {
  return (
    <>
      <header className="app-header">
        <NavLink to="/" className="app-brand" end>
          TestScope AI
        </NavLink>
        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
            New analysis
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : undefined)}>
            History
          </NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
