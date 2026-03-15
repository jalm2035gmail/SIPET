import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ahorrosIcon from '../assets/icons/custom/ahorros.svg'
import analiticaIcon from '../assets/icons/custom/analitica.svg'
import configuracionIcon from '../assets/icons/custom/configuracion.svg'
import creditosIcon from '../assets/icons/custom/creditos.svg'
import dashboardIcon from '../assets/icons/custom/dashboard.svg'
import sociosIcon from '../assets/icons/custom/socios.svg'

export default function MainLayout() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const menuItems = [
    { label: 'Dashboard', icon: dashboardIcon, to: '/backend' },
    { label: 'Dashboards 1.8', icon: dashboardIcon, to: '/backend/dashboards' },
    { label: 'Socios', icon: sociosIcon, to: '/backend/socios' },
    { label: 'Créditos', icon: creditosIcon, to: '/backend/creditos' },
    { label: 'Ahorros', icon: ahorrosIcon, to: '/backend/ahorros' },
    { label: 'Analítica', icon: analiticaIcon, to: '/backend/campanas' },
    { label: 'Configuración', icon: configuracionIcon, to: '/backend' }
  ]

  const handleLogout = () => {
    logout()
    navigate('/backend/login')
  }

  return (
    <div className="main-layout">
      <aside className="main-sidebar">
        <div className="main-sidebar__brand">Intellicoop</div>
        <nav className="main-sidebar__nav">
          {menuItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.to === '/backend'}
              className={({ isActive }) => `main-sidebar__link${isActive ? ' is-active' : ''}`}
            >
              <img src={item.icon} alt="" aria-hidden="true" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main-content">
        <header className="main-topbar">
          <nav>
            <button type="button" className="main-topbar__logout" onClick={handleLogout}>
              Cerrar sesión
            </button>
          </nav>
        </header>
        <main className="main-body">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
