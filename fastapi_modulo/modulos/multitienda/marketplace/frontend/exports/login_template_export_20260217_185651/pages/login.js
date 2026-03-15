import { useState } from 'react';
import axios from 'axios';
import styles from '../styles/login.module.css';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
  const imageUrl = `${apiBaseUrl}/static/imagenes/login.png`;
  const logoUrl = `${apiBaseUrl}/static/imagenes/tu-negocio.png`;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!username.trim() || !password) {
      setErrorMessage('Ingresa usuario y contraseña.');
      return;
    }

    setLoading(true);
    try {
      const payload = new URLSearchParams({
        username: username.trim(),
        password,
      });

      const response = await axios.post(
        `${apiBaseUrl}/avan/users/login`,
        payload.toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      const token = response?.data?.access_token;
      if (!token) {
        setErrorMessage('No se recibió token de acceso.');
        return;
      }

      localStorage.setItem('access_token', token);
      localStorage.setItem('token_type', response?.data?.token_type || 'bearer');
      setSuccessMessage('Inicio de sesión correcto.');
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setErrorMessage(
        typeof detail === 'string'
          ? detail
          : 'No se pudo iniciar sesión. Verifica credenciales.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <div className={styles.formSide}>
          <div className={styles.loginCard}>
            <div className={styles.logoWrap}>
              <img src={logoUrl} alt="Tu Negocio" />
            </div>
            <div className={styles.separator} />

            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldHeader}>
                  <label htmlFor="login-username">Correo electrónico</label>
                  <button className={styles.inlineLink} type="button">Elija un usuario</button>
                </div>
                <input
                  id="login-username"
                  type="text"
                  placeholder="alopez@avancoop.org"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                />
              </div>

              <div className={styles.fieldGroup}>
                <div className={styles.fieldHeader}>
                  <label htmlFor="login-password">Contraseña</label>
                  <button className={styles.inlineLink} type="button">
                    Restablecer contraseña
                  </button>
                </div>
                <input
                  id="login-password"
                  type="password"
                  placeholder="•••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </div>

              <button className={styles.submitBtn} type="submit" disabled={loading}>
                {loading ? 'Ingresando...' : 'Login'}
              </button>

              {errorMessage ? <p className={styles.errorText}>{errorMessage}</p> : null}
              {successMessage ? <p className={styles.successText}>{successMessage}</p> : null}
            </form>

            <p className={styles.signupText}>¿No tiene una cuenta?</p>
          </div>
        </div>

        <div className={styles.heroSide}>
          <div className={styles.heroImage} style={{ backgroundImage: `url('${imageUrl}')` }}>
            <div className={styles.heroOverlay} />
            <div className={styles.heroCopy}>
              <h2>Gestiona tu negocio</h2>
              <p>Organiza ventas, inventario y contabilidad en un solo lugar.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
