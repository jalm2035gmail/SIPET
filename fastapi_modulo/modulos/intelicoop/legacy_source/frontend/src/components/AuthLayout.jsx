import { Link, Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="auth-layout">
      <header className="auth-layout__header">
        <Link to="/web" className="auth-layout__brand">
          Intellicoop
        </Link>
      </header>

      <main className="auth-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
