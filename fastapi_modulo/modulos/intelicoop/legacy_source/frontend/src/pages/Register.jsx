import { useState } from 'react'
import { Link } from 'react-router-dom'

import Button from '../components/Button'
import Card from '../components/Card'

export default function Register() {
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
  }

  return (
    <section className="auth-page">
      <Card title="Registro de usuario">
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="nombre">Nombre completo</label>
          <input
            id="nombre"
            type="text"
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            placeholder="Nombre Apellido"
          />

          <label htmlFor="register-email">Correo</label>
          <input
            id="register-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="correo@intellicoop.com"
          />

          <label htmlFor="register-password">Contraseña</label>
          <input
            id="register-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="********"
          />

          <div className="auth-actions">
            <Button type="submit" variant="primary">
              Crear cuenta
            </Button>
            <Link to="/backend/login">Ya tengo cuenta</Link>
          </div>
        </form>
      </Card>
    </section>
  )
}
