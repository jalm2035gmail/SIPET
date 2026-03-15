import { Link, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="app-layout">
      <header className="app-navbar">
        <div className="brand">Intellicoop</div>
        <nav>
          <Link to="/backend">Inicio</Link>
          <Link to="/backend/login">Login</Link>
          <Link to="/backend/register">Registro</Link>
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
