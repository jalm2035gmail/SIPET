import { Link, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="app-layout">
      <header className="app-navbar">
        <div className="brand">Intellicoop</div>
        <nav>
          <Link to="/web">Inicio</Link>
          <Link to="/web/login">Login</Link>
          <Link to="/web/register">Registro</Link>
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <small>Intellicoop Local</small>
      </footer>
    </div>
  )
}
