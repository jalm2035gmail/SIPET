import { useState } from 'react'
import { Link } from 'react-router-dom'

import Button from '../components/Button'
import Card from '../components/Card'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
  }

  return (
    <section className="auth-page">
      <Card title="Recuperar contraseña">
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="forgot-email">Correo</label>
          <input
            id="forgot-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="correo@intellicoop.com"
          />

          <div className="auth-actions">
            <Button type="submit" variant="primary">
              Enviar enlace
            </Button>
            <Link to="/backend/login">Volver a login</Link>
          </div>
        </form>
      </Card>
    </section>
  )
}
