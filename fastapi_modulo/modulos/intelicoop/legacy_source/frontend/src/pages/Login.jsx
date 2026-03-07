import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { djangoApi } from '../services/api_django'
import styles from './loginTemplate.module.css'
import heroImage from '../assets/images/login_template/login.png'
import logoImage from '../assets/images/login_template/tu-negocio.png'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false)

  const handleSubmit = (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    djangoApi
      .post('/auth/login/', {
        username: identifier,
        password,
        otp_code: otpCode
      })
      .then((response) => {
        login({
          access: response.data?.access,
          refresh: response.data?.refresh
        })
        setRequiresTwoFactor(false)
        setOtpCode('')
        setSuccess('Inicio de sesión correcto.')
        navigate('/web')
      })
      .catch((requestError) => {
        if (requestError?.response?.data?.two_factor_required) {
          setRequiresTwoFactor(true)
          setError('Ingresa el código de autenticación de dos factores.')
          return
        }
        if (requestError?.response?.data?.otp_code) {
          setRequiresTwoFactor(true)
          setError('Código 2FA inválido o expirado.')
          return
        }
        setError('Credenciales inválidas. Verifica usuario y contraseña.')
      })
      .finally(() => setLoading(false))
  }

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <div className={styles.formSide}>
          <div className={styles.loginCard}>
            <div className={styles.logoWrap}>
              <img src={logoImage} alt="Tu Negocio" />
            </div>
            <div className={styles.separator} />

            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldHeader}>
                  <label htmlFor="identifier">Usuario o correo</label>
                  <Link className={styles.inlineLink} to="/web/register">
                    Crear cuenta
                  </Link>
                </div>
                <input
                  id="identifier"
                  type="text"
                  placeholder="usuario o correo@intellicoop.com"
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  autoComplete="username"
                />
              </div>

              <div className={styles.fieldGroup}>
                <div className={styles.fieldHeader}>
                  <label htmlFor="password">Contraseña</label>
                  <Link className={styles.inlineLink} to="/web/forgot-password">
                    Restablecer contraseña
                  </Link>
                </div>
                <input
                  id="password"
                  type="password"
                  placeholder="•••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </div>

              {requiresTwoFactor ? (
                <div className={styles.fieldGroup}>
                  <div className={styles.fieldHeader}>
                    <label htmlFor="otpCode">Código 2FA</label>
                  </div>
                  <input
                    id="otpCode"
                    type="text"
                    placeholder="000000"
                    value={otpCode}
                    onChange={(event) => setOtpCode(event.target.value)}
                    autoComplete="one-time-code"
                  />
                </div>
              ) : null}

              <button className={styles.submitBtn} type="submit" disabled={loading}>
                {loading ? 'Ingresando...' : requiresTwoFactor ? 'Verificar código' : 'Login'}
              </button>

              {error ? <p className={styles.errorText}>{error}</p> : null}
              {success ? <p className={styles.successText}>{success}</p> : null}
            </form>

            <p className={styles.signupText}>¿No tiene una cuenta?</p>
          </div>
        </div>

        <div className={styles.heroSide}>
          <div className={styles.heroImage} style={{ backgroundImage: `url('${heroImage}')` }}>
            <div className={styles.heroOverlay} />
            <div className={styles.heroCopy}>
              <h2>Gestiona tu negocio</h2>
              <p>Organiza ventas, inventario y contabilidad en un solo lugar.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
