import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import MainLayout from './components/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'
import PublicRoute from './components/PublicRoute'

const AuthLayout = lazy(() => import('./components/AuthLayout'))
const Home = lazy(() => import('./pages/Home'))
const SociosList = lazy(() => import('./pages/SociosList'))
const CreditosList = lazy(() => import('./pages/CreditosList'))
const AhorrosDashboard = lazy(() => import('./pages/AhorrosDashboard'))
const Dashboards18 = lazy(() => import('./pages/Dashboards18'))
const CampaniasList = lazy(() => import('./pages/CampaniasList'))
const ProspectosList = lazy(() => import('./pages/ProspectosList'))
const SociosInactivos = lazy(() => import('./pages/SociosInactivos'))
const CreditoForm = lazy(() => import('./pages/CreditoForm'))
const CreditoDetail = lazy(() => import('./pages/CreditoDetail'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))

export default function App() {
  return (
    <Suspense fallback={<div className="route-loading">Cargando módulo...</div>}>
      <Routes>
        <Route
          path="/web"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Home />} />
          <Route path="socios" element={<SociosList />} />
          <Route path="creditos" element={<CreditosList />} />
          <Route path="ahorros" element={<AhorrosDashboard />} />
          <Route path="dashboards" element={<Dashboards18 />} />
          <Route path="campanas" element={<CampaniasList />} />
          <Route path="prospectos" element={<ProspectosList />} />
          <Route path="socios-inactivos" element={<SociosInactivos />} />
          <Route path="creditos/nuevo" element={<CreditoForm />} />
          <Route path="creditos/:id" element={<CreditoDetail />} />
        </Route>
        <Route
          path="/web"
          element={
            <PublicRoute>
              <AuthLayout />
            </PublicRoute>
          }
        >
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />
          <Route path="forgot-password" element={<ForgotPassword />} />
        </Route>
        <Route path="/" element={<Navigate to="/web" replace />} />
        <Route path="*" element={<Navigate to="/web" replace />} />
      </Routes>
    </Suspense>
  )
}
